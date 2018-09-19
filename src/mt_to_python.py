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

import mt_visitor

class MTpython(mt_visitor.MTvisitor):
    def __init__(self):
        super().__init__()
        self.seen = { }  # { (addr, typename): python }

    def get(self, symbol_value):
        """ return a python structure from symbol (symbol, value) """
        value = symbol_value[1]

        # start recursion
        self.stack = [] # (name, python)
        self.visit(value, symbol_value[0].name)
        assert len(self.stack) == 1
        return self.stack[0][1]

    def visit_struct(self, value, name):
        struct = { }
        if self._cached(value, name, struct): return

        stack = self.stack
        self.stack = []
        self.generic_visit(value, name)
        for k, v in self.stack:
            if k[0] == '[': k = int(k[1 : k.find(']')])
            struct[k] = v
        self.stack = stack
        self.stack.append((name, struct))

    def visit_array(self, value, name):
        if self.is_string_char_array(value):
            # do not create another dict for the string
            return self.visit_string(value, name)
        else:
            self.visit_struct(value, name)

    def visit_union(self, value, name):
        self.visit_struct(value, name)

    def visit_ptr(self, value, name):
        stack = self.stack
        self.stack = []
        self.generic_visit(value, name)
        if len(self.stack):
            v = self.stack[0][1]
        else:
            v = None
        self.stack = stack
        self.stack.append((name, v))

    def visit_int(self, value, name):
        self.stack.append((name, int(value)))

    def visit_char(self, value, name):
        self.stack.append((name, str(value)))

    def visit_string(self, value, name):
        try:
            string = value.string()
        except:
            string = None
        self.stack.append((name, string))

    def visit_bool(self, value, name):
        self.stack.append((name, bool(value)))

    def visit_flt(self, value, name):
        self.stack.append((name, float(value)))

    def visit_enum(self, value, name):
        self.stack.append((name, int(value)))

    def _cached(self, value, name, python):
        if value.address:
            addr = int(value.address)
            if addr:
                typename = str(value.type)
                key = (addr, typename)
                if key in self.seen.keys():
                    self.stack.append((name, self.seen[key]))
                    return True
                else:
                    self.seen[key] = python
        return False
