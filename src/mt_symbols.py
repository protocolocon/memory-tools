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

import gdb, os, mt_colors as c
from mt_type_cleaning import clean_type

class MTsymbols:
    """
    Find all symbols accessible from the blocks of all frames of all threads.
    """

    def __init__(self, empty = False):
        self.symbols_by_name = { }        # { name: { address: (symbol, thread, frame, block) } }
        self.symbols_by_addr = { }        # { address: { name: (symbol, thread, frame, block) } }
        if not empty: self._inferior()

    def dump(self):
        print(c.WHITE + 'symbols' + c.RESET)
        addrs = list(self.symbols.keys())
        addrs.sort()
        for addr in addrs:
            symbol, value = self.symbols[addr]
            print((c.GREEN + '%16x ' + c.YELLOW + '%10d ' + c.RESET + '%-40s %s') %
                  (int(value.address), value.type.sizeof, symbol.name, clean_type(value.type)))
        print()

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
            raise RuntimeError('inferior not assigned')

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
        for symbol in block:
            self._symbol(symbol, block, frame, thread)

    def _symbol(self, symbol, block, frame, thread):
        # self.symbols = { name: { address: (symbol, thread, frame, block) } }
        addr = 0
        if symbol.addr_class not in [gdb.SYMBOL_LOC_TYPEDEF, gdb.SYMBOL_LOC_UNRESOLVED]:
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
