#   -*- mode: python; coding: utf-8; -*-
#
#   Copyright 2018 Asier Aguirre <asier.aguirre@gmail.com>
#   This file is part of memory-tools.
#
#   memory-tools is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   memory-tools is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with memory-tools. If not, see <http://www.gnu.org/licenses/>.

import gdb, os, re, mt_maps
from mt_type_cleaning import clean_type
from mt_colors import mt_colors as c

mt_symbol_loc_to_name = {
    gdb.SYMBOL_LOC_UNDEF:            'loc_undef',
    gdb.SYMBOL_LOC_CONST:            'loc_const',
    gdb.SYMBOL_LOC_STATIC:           'loc_static',
    gdb.SYMBOL_LOC_REGISTER:         'loc_register',
    gdb.SYMBOL_LOC_ARG:              'loc_arg',
    gdb.SYMBOL_LOC_REF_ARG:          'loc_ref_arg',
    gdb.SYMBOL_LOC_REGPARM_ADDR:     'loc_regparm_addr',
    gdb.SYMBOL_LOC_LOCAL:            'loc_local',
    gdb.SYMBOL_LOC_TYPEDEF:          'loc_typedef',
    gdb.SYMBOL_LOC_BLOCK:            'loc_block',
    gdb.SYMBOL_LOC_CONST_BYTES:      'loc_const_bytes',
    gdb.SYMBOL_LOC_UNRESOLVED:       'loc_unresolved',
    gdb.SYMBOL_LOC_OPTIMIZED_OUT:    'loc_optimized_out',
    gdb.SYMBOL_LOC_COMPUTED:         'loc_computed',
}

mt_frame_type_to_name = {
    gdb.NORMAL_FRAME:                'frame_normal',
    gdb.DUMMY_FRAME:                 'frame_dummy',
    gdb.INLINE_FRAME:                'frame_inline',
    gdb.TAILCALL_FRAME:              'frame_tailcall',
    gdb.SIGTRAMP_FRAME:              'frame_sigtramp',
    gdb.ARCH_FRAME:                  'frame_arch',
    gdb.SENTINEL_FRAME:              'frame_sentinel',
}

class MTsymbols:
    """
    Find all symbols accessible from the blocks of all frames of all threads.
    """

    def __init__(self, empty = False):
        self.symbols_by_name = { }        # { name: { address: (symbol, thread, frame, block) } }
        self.symbols_by_addr = { }        # { address: { name: (symbol, thread, frame, block) } }
        self.seen_global_blocks = set()   # { (start, end) }
        if not empty: self._inferior()

    def filter_arguments_from_string(self, argument):
        locs = set()
        addrs = set()
        names = [ ]
        ranges = [ ]
        name_to_loc = { v: k for k, v in mt_symbol_loc_to_name.items() }
        for arg in argument.split():
            if arg in name_to_loc.keys():
                locs.add(name_to_loc[arg])
            else:
                try:
                    if '-' in arg: # range
                        a = [int(x, base = 0) for x in arg.split('-')]
                        ranges.append((a[0], a[1]))
                    else: # address
                        addr = int(arg, base = 0)
                        addrs.add(addr)
                except ValueError:
                    names.append(arg)
        return locs, addrs, names, ranges

    def filter(self, locs = set(), addresses = set(), names = [ ], ranges = [ ]):
        syms = []
        if (not locs and not addresses and not ranges and len(names) == 1 and
            names[0].startswith('^') and names[0].endswith('$') and re.match('^[a-zA-Z0-9_]*$', names[0][1:-1]) and
            names[0][1:-1] in self.symbols_by_name.keys()):
            # fast matching: only name
            for address, tup in self.symbols_by_name[names[0][1:-1]].items():
                syms.append((address, names[0][1:-1], tup))
        else:
            # slow matching
            def match_name(name):
                for n in names:
                    if re.match(n, name):
                        return True
                return False
            def match_range(address):
                for r in ranges:
                    if address >= r[0] and address < r[1]:
                        return True
                return False
            for name, address_dict in self.symbols_by_name.items():
                if not names or match_name(name):
                    for address, tup in address_dict.items():
                        if ((not locs or tup[0].addr_class in locs) and
                            (not addresses or address in addresses) and
                            (not ranges or match_range(address))):
                            syms.append((address, name, tup))
            syms.sort()
        return syms

    def dump_tuples(self, tuple_syms):
        p = lambda x, c: x and c or ' '
        cut = lambda x, length: len(x) > length and x[:length - 3] + '...' or x
        print(c.white + 'symbols' + c.reset)
        if tuple_syms:
            print((c.cyan + '%16s%8s %s %-40s %s' + c.reset) % ('Address', 'Sizeof', 'ACV', 'Name', 'Symbol type + Type (A=arg, C=const, V=variable)'))
        for address, name, (symbol, thread, frame, block) in tuple_syms:
            print((c.green + '%16x' + c.yellow + '%8d ' + c.cyan + '%s%s%s ' +
                   c.reset + '%-40s ' + c.blue + '%s ' + c.reset + '%s') %
                  (address, symbol.type.sizeof,
                   p(symbol.is_argument, 'A'), p(symbol.is_constant, 'C'), p(symbol.is_variable, 'V'),
                   cut(name, 40), mt_symbol_loc_to_name[symbol.addr_class], clean_type(symbol.type)))

    def dump_value(self, tuple_sym):
        addr, name, (symbol, thread, frame, block) = tuple_sym
        thread.switch() # leave thread selected
        params = [ ('name',           c.cyan + name + c.reset),
                   ('linkage',        symbol.linkage_name),
                   ('address',        hex(addr)),
                   ('type',           str(symbol.type)),
                   ('source',         symbol.symtab.filename + ':' + str(symbol.line)),
                   ('obj',            (symbol.symtab.objfile.owner and
                                      symbol.symtab.objfile.owner.filename or
                                      symbol.symtab.objfile.filename)),
                   ('sym type',       mt_symbol_loc_to_name[symbol.addr_class]),
                   ('props',          ((symbol.needs_frame and 'frame ' or '') +
                                       (symbol.is_argument and 'argument ' or '') +
                                       (symbol.is_constant and 'constant ' or '') +
                                       (symbol.is_function and 'function ' or '') +
                                       (symbol.is_variable and 'variable ' or ''))),
                   ('thread',         c.cyan + str(thread.num) + c.reset),
                   ('  name',         thread.name),
                   ('  pid',          str(thread.ptid[0])),
                   ('  lwpid',        str(thread.ptid[1])),
                   ('  tid',          str(thread.ptid[2])),
        ]
        # frame
        if symbol.needs_frame:
            frame.select()
            frame_num = -1
            f = frame
            while f and f.is_valid():
                f = f.newer()
                frame_num += 1
            frame.select() # leave frame selected
            params += [
                ('frame',             c.cyan + str(frame_num) + c.reset),
                ('  name',            str(frame.name())),
                ('  type',            mt_frame_type_to_name[frame.type()]),
                ('  pc',              hex(frame.pc())),
                ('  source',          frame.find_sal().symtab.filename + ':' + str(frame.find_sal().line)),
            ]
        # memory mapping
        maps = mt_maps.MTmaps()
        reg = maps.get_region(addr)
        if reg:
            params += [
                ('map',               ''),
                ('  low',             hex(reg[0])),
                ('  high',            hex(reg[1])),
                ('  descr',           reg[2]),
            ]
        # value
        if symbol.addr_class not in { gdb.SYMBOL_LOC_TYPEDEF, gdb.SYMBOL_LOC_UNRESOLVED, gdb.SYMBOL_LOC_LABEL }:
            value = symbol.value(frame)
            params += [ ('value', c.cyan + str(value) + c.reset) ]

        # dump finally everything
        print(c.white + 'value' + c.reset)
        for k, v in params:
            print((c.green + '  %-15s ' + c.reset + '%s') % (k + ':', v))

    def dump_stats(self):
        d = { }
        print(c.white + 'symbol stats by symbol type' + c.reset)
        for name, address_dict in self.symbols_by_name.items():
            for address, tup in address_dict.items():
                d[tup[0].addr_class] = d.get(tup[0].addr_class, 0) + 1
        for loc, number in d.items():
            print((c.cyan + '  %-17s' + c.yellow + '%7d' + c.reset) % (mt_symbol_loc_to_name[loc], number))

    def filter_by_regions(self, regions):
        """ regions as in MTmaps regions """
        symbols = MTsymbols(True)
        filtered = symbols.symbols
        for address, symbol in self.symbols.items():
            for region in regions:
                if address >= region[0] and address < region[1]:
                    filtered[address] = symbol
                    break
        return symbols

    def filter_by_providers(self, providers):
        """ providers are just binary or libraries base names """
        symbols = MTsymbols(True)
        filtered = symbols.symbols
        for address, (symbol, value) in self.symbols.items():
            provider = symbol.symtab.objfile.owner and symbol.symtab.objfile.owner.filename or symbol.symtab.objfile.filename
            provider = os.path.basename(provider)
            if provider in providers:
                filtered[address] = (symbol, value)
        return symbols

    def find_symbol_by_name(self, name):
        """ return the dict { address: (symbol, thread, frame, block) } with specified name"""
        return self.symbols_by_name.get(name, { })

    def find_symbol_value_by_name(self, name):
        """ return the list of [ (symbol, value) ] with specified name"""
        symb_val = []
        for v in self.find_symbol_by_name(name).values():
            v[1].switch() # thread switch
            symb_val.append((v[0], v[0].value(v[2])))
        return symb_val

    def _inferior(self):
        # get inferior
        inferior = gdb.selected_inferior()
        if not inferior or not inferior.is_valid():
            raise RuntimeError('no inferior or invalid')
        if not inferior.pid:
            raise RuntimeError('inferior not running')

        # get threads
        threads = inferior.threads()

        # analyse threads
        for thread in threads:
            self._thread(thread)

    def _thread(self, thread):
        thread.switch()
        assert thread.is_valid()
        frame = gdb.newest_frame()
        while frame:
            try:
                block = frame.block()
            except:
                block = None

            # blocks
            self._frame(block, frame, thread)

            assert frame.is_valid()
            frame = frame.older()

    def _frame(self, block, frame, thread):
        while block and block.is_valid():
            self._block(block, frame, thread)
            block = block.superblock

    def _block(self, block, frame, thread):
        if block.is_global:
            # do not parse multiple times the same blocks
            block_key = (block.start, block.end)
            if block_key in self.seen_global_blocks: return
            self.seen_global_blocks.add(block_key)

        for symbol in block:
            self._symbol(symbol, block, frame, thread)

    def _symbol(self, symbol, block, frame, thread):
        # self.symbols = { name: { address: (symbol, thread, frame, block) } }
        addr = 0
        if symbol.addr_class not in { gdb.SYMBOL_LOC_TYPEDEF, gdb.SYMBOL_LOC_UNRESOLVED, gdb.SYMBOL_LOC_LABEL }:
            value = symbol.value(frame)
            if value.address != None and not value.is_optimized_out:
                addr = int(value.address)
        name = symbol.name
        self.symbols_by_name.setdefault(name, { }).setdefault(addr, (symbol, thread, frame, block))
        self.symbols_by_addr.setdefault(addr, { }).setdefault(name, (symbol, thread, frame, block))
        sq_br = name.find('[')
        if sq_br > 0:
            # store also removing ABI info
            name = name[: sq_br]
            self.symbols_by_name.setdefault(name, { }).setdefault(addr, (symbol, thread, frame, block))
            self.symbols_by_addr.setdefault(addr, { }).setdefault(name, (symbol, thread, frame, block))
