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

import gdb

def show_exception(func):
    def wrap(self, args, from_tty):
        try:
            return func(self, args, from_tty)
        except Exception as e:
            print('exception', e)
            raise e
    return wrap

class MT(gdb.Command):
    'Memory tools commands'
    def __init__(self):
        gdb.Command.__init__ (self, 'mt', gdb.COMMAND_DATA, prefix = True)

    def dont_repeat():
        pass

    def invoke(self, argument, from_tty):
        pass


class MTfind_symbol(gdb.Command):
    'Find a symbol by name'
    def __init__(self):
        gdb.Command.__init__ (self, 'mt find_symbol', gdb.COMMAND_DATA, prefix = False)

    def dont_repeat():
        pass

    @show_exception
    def invoke(self, argument, from_tty):
        print('symbol', gdb.lookup_symbol(argument))

MT()
MTfind_symbol()
