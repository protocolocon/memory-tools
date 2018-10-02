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

import gdb, sys, mt_maps, mt_symbols
from mt_colors import mt_colors as c


# context
class MTcontext:
    def __init__(self):
        self.invalidate()

    def invalidate(self):
        self.maps = None
        self.symbols = None

    def get_maps(self):
        if self.maps: return self.maps
        self.maps = mt_maps.MTmaps()
        return self.maps

    def get_symbols(self):
        if self.symbols: return self.symbols
        self.symbols = mt_symbols.MTsymbols()
        return self.symbols

mt_context = MTcontext()
mt_debug = False

def mt_show_exception(func):
    def wrap(self, args, from_tty):
        try:
            return func(self, args, from_tty)
        except Exception as e:
            print(c.red + 'internal error:' + c.reset, e)
            if mt_debug:
                # print traceback
                try:
                    import traceback
                    traceback.print_tb(sys.exc_info()[2])
                except:
                    pass
    return wrap


class MTbase(gdb.Command):
    def dont_repeat(self):
        pass


class MT(MTbase):
    """Memory tools commands
    With no subcomands, print extensive help and statistics.
    """
    def __init__(self):
        gdb.Command.__init__(self, 'mt', gdb.COMMAND_DATA, prefix = True)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        print(c.white + 'memory-tools' + c.reset)
        inferior = gdb.selected_inferior()
        if inferior and inferior.is_valid() and inferior.pid:
            maps = mt_context.get_maps()
            syms = mt_context.get_symbols()
            print(c.cyan + '  maps: ' + c.reset + str(len(maps.regions)))
            print(c.cyan + '  symbols: ' + c.reset + str(len(syms.filter())))
        else:
            print(c.red + '  error: ' + c.reset + 'inferior not valid (start program, open core or attach to running)')


class MTsymbols(MTbase):
    """Locate and dump symbols (searching in all active blocks)
    With no arguments, dump symbol statistics.
    Use single argument * to dump all symbols except types, blocks and constants.
    Use single argument ** to dump all symbols.
    Arguments can be addresses, ranges, name regexes and/or location types.
    When one or more of these argument types are used, symbols matching one
      of each type are dumped.
    Ranges are of the form: addr0-addr1.
    Note: use one parameter of the form '^variable_name$' for fast matching.
    Examples:
      mt symbols # dump stats
      mt symbols loc_static loc_computed loc_optimized_out
      mt symbols ^var_ loc_static # static symbols matching regex ^var_
      mt symbols *
      mt symbols 0x804acb0-0x8064468 # all in range
    """
    def __init__(self):
        gdb.Command.__init__(self, 'mt symbols', gdb.COMMAND_DATA, prefix = False)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        syms = mt_context.get_symbols()
        if not argument:
            syms.dump_stats()
        else:
            locs, addrs, names, ranges = syms.filter_arguments_from_string(argument)
            syms.dump_tuples(syms.filter(locs, addrs, names, ranges))


class MTvalue(MTbase):
    """Dump all possible information on a symbol value
    Arguments can be addresses, ranges, name regexes and/or location types.
    When one or more of these argument types are used, first symbol matching
      one of each type will be selected.
    Ranges are of the form: addr0-addr1.
    Examples:
      mt value variable_name # name regex
      mt value ^var[123]     # name regex
      mt value 0x804acb0-0x8064468 loc_static # first static variable in range
    """
    def __init__(self):
        gdb.Command.__init__(self, 'mt value', gdb.COMMAND_DATA, prefix = False)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        syms = mt_context.get_symbols()
        locs, addrs, names, ranges = syms.filter_arguments_from_string(argument)
        tuples = syms.filter(locs, addrs, names, ranges)
        if not tuples:
            print(c.red + 'error: ' + c.reset + 'no matching symbol')
        else:
            if len(tuples) > 1:
                print(c.brown + 'warning: ' + c.reset +
                      'several (' + str(len(tuples)) + ') matching symbols, dumping first')
            syms.dump_value(tuples[0], mt_context.get_maps())


class MTmaps(MTbase):
    """Dump memory mappings (inferring all heaps and stacks)
    With no arguments print all inferior memory mappings: /proc/<pid>/maps.
    With an integral parameter, only the mapping containing address is dumped.
    With a sequence of filenames (basenames), those file mappings are dumped.
    Examples:
      mt maps 0x7ffffffde000
      mt maps libc-2.27.so libpthread-2.27.so [heap] [stack]
    """
    def __init__(self):
        gdb.Command.__init__(self, 'mt maps', gdb.COMMAND_DATA, prefix = False)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        maps = mt_context.get_maps()
        if not argument:
            maps.dump()
        else:
            try:
                addr = int(argument, base = 0)
                maps.dump([maps.get_region(addr)])
            except ValueError:
                maps.dump(maps.get_regions(argument.split()))


class MTcolors(MTbase):
    """De/activate and configure usage of console colors (escape sequences)
    Without arguments, it switches colors on and off.
    Use 'on' and 'off' to explicitly enable or dissable colors.
    Use 'list' to display current configuration of colors.
    Use <color name> 'sequence' to configure a color.
    Example:
      mt colors off
      mt colors list
      mt colors cyan \\033[35m
    """
    def __init__(self):
        gdb.Command.__init__(self, 'mt colors', gdb.COMMAND_DATA, prefix = False)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        c.use(argument, from_tty)


class MTdebug(MTbase):
    """De/activate own debug of memory-tools
    Without arguments, it switches debug on and off.
    Explicitly set on / off to enable or disable debug.
    Example:
      mt debug off
    """
    def __init__(self):
        gdb.Command.__init__(self, 'mt debug', gdb.COMMAND_DATA, prefix = False)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        global mt_debug
        if not argument:
            mt_debug = not mt_debug
            if from_tty: print(c.cyan + 'debug: ' + c.green + (mt_debug and 'ON' or 'OFF') + c.reset)
        elif argument.lower() == 'on':
            mt_debug = True
        elif argument.lower() == 'off':
            mt_debug = False
        else:
            print(c.red + 'error: ' + c.reset + 'unknown argument "' + argument + '"')


class MTtest(MTbase):
    """Internal testing"""
    def __init__(self):
        gdb.Command.__init__(self, 'mt test', gdb.COMMAND_DATA, prefix = False)

    @mt_show_exception
    def invoke(self, argument, from_tty):
        pass


# register event handler to invalidate context
# every time inferior runs, context gets invalidated
# so that symbols, maps, etc, are recomputed on demand
# otherwise, multiple commands benefit from cached results
def mt_invalidation_handler(event): mt_context.invalidate()
gdb.events.cont.connect(mt_invalidation_handler)


# register commands
mt_commands = {
    'mt':          MT(),
    'mt_symbols':  MTsymbols(),
    'mt_value':    MTvalue(),
    'mt_maps':     MTmaps(),
    'mt_colors':   MTcolors(),
    'mt_debug':    MTdebug(),
    #'mt_test':     MTtest(),
}
