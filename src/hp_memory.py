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

import hp_visitor

class HPmemory(hp_visitor.HPvisitor):
    def __init__(self):
        super().__init__()
        self.seen = { }    # { (addr, size): name }
        self.graph = set() # { (addr_from, addr_to) }

    def analysis(self, symbols):
        """ memory analysis; symbols is a HPsymbols object """
        for addr, (symbol, value) in symbols.symbols.items():
            # start recursion for this value
            self.stack = [] # [ (name, address) ]
            self.visit(value, symbol.name)
            assert len(self.stack) == 1, 'memory analysis value'

        # debug
        print(len(self.seen), len(self.graph))
        addrs = [ (addr, size, name) for (addr, size), name in self.seen.items() ]
        addrs = sorted(addrs, key = lambda x: (x[0] << 16) - x[1])
        for i, (addr, size, name) in enumerate(addrs):
            indent = 0
            j = i - 1
            while j >= 0 and addr < addrs[j][0] + addrs[j][1]:
                j -= 1
                indent += 1
            print("%016x %s %s" % (addr, '    '*indent, name))

    def process(self, value, name, recur):
        addr = int(value.address or 0)
        if addr:
            size = value.type.sizeof
            key = (addr, size)
            if key not in self.seen.keys():
                self.seen[key] = name
                if recur: # visit dependencies
                    stack = self.stack
                    self.stack = []
                    self.generic_visit(value, name)
                    for name, address in self.stack:
                        if address and (name[0] == '[' or name[0] == '*'):
                            self.graph.add((addr, address))
                    self.stack = stack
        self.stack.append((name, addr))

    def visit_struct (self, value, name): self.process(value, name, True)
    def visit_array  (self, value, name): self.process(value, name, True)
    def visit_union  (self, value, name): self.process(value, name, True)
    def visit_ptr    (self, value, name): self.process(value, name, True)
    def visit_int    (self, value, name): self.process(value, name, False)
    def visit_char   (self, value, name): self.process(value, name, False)
    def visit_string (self, value, name): self.process(value, name, False)
    def visit_bool   (self, value, name): self.process(value, name, False)
    def visit_flt    (self, value, name): self.process(value, name, False)
    def visit_enum   (self, value, name): self.process(value, name, False)
