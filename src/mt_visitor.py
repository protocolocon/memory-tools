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
from mt_containers import (Array, StdVector, StdUnorderedMap, StdUniquePtr, StdSharedPtr, StdString, StdMutex,
                           StdList, StdFunction, FrameLFHashMap, FrameLFVector, FrameLFChunk, FrameHashMapCloseAddressing)

codeToName = {
    gdb.TYPE_CODE_PTR:               'ptr',               #  1
    gdb.TYPE_CODE_ARRAY:             'array',             #  2
    gdb.TYPE_CODE_STRUCT:            'struct',            #  3
    gdb.TYPE_CODE_UNION:             'union',             #  4
    gdb.TYPE_CODE_ENUM:              'enum',              #  5
    gdb.TYPE_CODE_FLAGS:             'flags',             #  6
    gdb.TYPE_CODE_FUNC:              'func',              #  7
    gdb.TYPE_CODE_INT:               'int',               #  8
    gdb.TYPE_CODE_FLT:               'flt',               #  9
    gdb.TYPE_CODE_VOID:              'void',              # 10
    gdb.TYPE_CODE_SET:               'set',               # 11
    gdb.TYPE_CODE_RANGE:             'range',             # 12
    gdb.TYPE_CODE_STRING:            'string',            # 13
    gdb.TYPE_CODE_BITSTRING:         'bitstring',         # -1
    gdb.TYPE_CODE_ERROR:             'error',             # 14
    gdb.TYPE_CODE_METHOD:            'method',            # 15
    gdb.TYPE_CODE_METHODPTR:         'methodptr',         # 16
    gdb.TYPE_CODE_MEMBERPTR:         'memerptr',          # 17
    gdb.TYPE_CODE_REF:               'ref',               # 18
    gdb.TYPE_CODE_CHAR:              'char',              # 19
    gdb.TYPE_CODE_BOOL:              'bool',              # 20
    gdb.TYPE_CODE_COMPLEX:           'complex',           # 21
    gdb.TYPE_CODE_TYPEDEF:           'typedef',           # 22
    gdb.TYPE_CODE_NAMESPACE:         'namespace',         # 23
    gdb.TYPE_CODE_DECFLOAT:          'decfloat',          # 24
    gdb.TYPE_CODE_INTERNAL_FUNCTION: 'internal_function', # 26
}


class MTvisitor:
    def __init__(self, n_elems_containters = 1 << 32):
        self.n_elems_containers = n_elems_containters
        self.char_type = gdb.lookup_type('char')
        self.long_type = gdb.lookup_type('long')

    def visit(self, value, name):
        code = value.type.code
        func_name = 'visit_' + codeToName.get(code, 'unhandled')
        if hasattr(self, func_name):
            getattr(self, func_name)(value, name)
        else:
            self.generic_visit(value, name)

    def visit_string(self, value, name):
        pass

    def generic_visit(self, value, name):
        visitors = {
            gdb.TYPE_CODE_PTR:       self._ptr_visit,
            gdb.TYPE_CODE_ARRAY:     self._array_visit,
            gdb.TYPE_CODE_STRUCT:    self._struct_visit,
            gdb.TYPE_CODE_UNION:     self._union_visit,
            gdb.TYPE_CODE_FUNC:      self._func_visit,
            gdb.TYPE_CODE_METHODPTR: self._methodptr_visit,
            gdb.TYPE_CODE_REF:       self._ref_visit,
            gdb.TYPE_CODE_TYPEDEF:   self._typedef_visit,
        }
        def unhandled(value, name):
            print('missing type code:', codeToName[value.type.code])

        visitors.get(value.type.code, unhandled)(value, name)

    def _struct_visit(self, value, name):
        # check for specific containers
        typename = value.type.name or ''
        if typename.startswith('std::'):
            if typename.startswith('std::vector<'):
                vector = StdVector(value)
                return self._common_generator(vector, 'std::vector')
            elif typename.startswith('std::unordered_map<'):
                um = StdUnorderedMap(value)
                return self._common_generator(um, 'std::unordered_map')
            elif typename.startswith('std::unordered_set<'):
                us = StdUnorderedMap(value)
                return self._common_generator(us, 'std::unordered_set')
            elif typename.startswith('std::unique_ptr<'):
                up = StdUniquePtr(value)
                self.visit_string(gdb.Value('std::unique_ptr'), '.type')
                if up.valid(): self.visit(up.get_elem(), '*')
                return
            elif typename.startswith('std::shared_ptr<'):
                sp = StdSharedPtr(value)
                self.visit_string(gdb.Value('std::shared_ptr'), '.type')
                self.visit(gdb.Value(sp.ref_count()), '.ref_count')
                if sp.valid():
                    self.visit(sp.get_elem(), '*')
                return
            elif typename.startswith('std::__cxx11::basic_string<') or typename.startswith('std::basic_string<'):
                string = StdString(value)
                self.visit_string(gdb.Value('std::string'), '.type')
                self.visit_string(gdb.Value(string.get()), '*')
                return
            elif typename == 'std::mutex' or typename == 'std::recursive_mutex':
                thread = StdMutex(value)
                locked = thread.locked()
                self.visit_string(gdb.Value('std::mutex'), '.type')
                self.visit(gdb.Value(locked), '.locked')
                if locked:
                    self.visit(gdb.Value(thread.owner()), '.owner')
                return
            elif typename.startswith('std::__cxx11::list<') or typename.startswith('std::list<'):
                lst = StdList(value)
                return self._common_generator(lst, 'std::list')
            elif typename.startswith('std::function<'):
                func = StdFunction(value)
                self.visit_string(gdb.Value('std::function'), '.type')
                if not func.empty():
                    self.visit(gdb.Value(func.address()), '*')
                return

        elif typename.startswith('boost::'):
            if typename.startswith('boost::multi_index::multi_index_container<'):
                return # TODO

        elif typename.startswith('frame::'):
            if typename.startswith('frame::lf::HashMap<') and typename[-1] == '>':
                hm = FrameLFHashMap(value)
                return self._common_generator(hm, 'frame::lf::HashMap')
            elif typename.startswith('frame::HashMapCloseAddressing<') and typename[-1] == '>':
                hm = FrameHashMapCloseAddressing(value)
                return self._common_generator(hm, 'frame::HashMapCloseAddressing')
            elif typename.startswith('frame::lf::Vector<'):
                vector = FrameLFVector(value)
                return self._common_generator(vector, 'frame::lf::Vector')
            elif typename == 'frame::lf::Chunk':
                chunk = FrameLFChunk(value)
                self.visit_string(gdb.Value('frame::lf::Chunk'), '.type')
                self.visit(gdb.Value(chunk.size()), '.size')
                self.visit(gdb.Value(chunk.capacity()), '.capacity')
                self.visit(gdb.Value(chunk.collected()), '.collected')
                return

        for field_name, field in value.type.items():
            if field.artificial: continue
            #print('Field:', name + '::' + field_name, field.type.code, field.type.name, field.is_base_class)
            if field.is_base_class:
                # inheritance
                if field.type.sizeof > 1: # only continue recursion if base has data members
                    base = value.cast(field.type)
                    self.visit(base, '.base')
            elif hasattr(field, 'bitpos'):
                # composition
                self.visit(value[field_name], field_name or '<anonymous>')
            else:
                # static member
                pass #print('missing static member')

    def _union_visit(self, value, name):
        for field_name, field in value.type.items():
            #print('Union:', name, field_name, field.type.code, field.type.name)
            self.visit(value[field_name], '+' + (field_name or '<anonymous>'))

    def _array_visit(self, value, name):
        array = Array(value)
        # special case, array of char -> string
        if array.type_elem.name == 'char':
            self.visit_string(value, name)
            return
        return self._common_generator(array, 'array')

    def _ptr_visit(self, value, name):
        base_type = value.type.target()
        # special case 'const char *'
        if base_type.name == 'char' and base_type == base_type.const():
            self.visit_string(value, name)
            return

        value = value.dereference()
        try:
            str(value.cast(self.char_type)) # test that values is in accessible memory
        except:
            #self.visit(value.cast(self.long_type), name) # visit with the pointer value
            return
        name = '*' + name
        self.visit(value, name)

    def _ref_visit(self, value, name):
        self.visit(value.referenced_value(), '&' + name)

    def _typedef_visit(self, value, name):
        self.visit(value.cast(value.type.strip_typedefs()), name)

    def _func_visit(self, value, name):
        self.visit(value.cast(self.long_type), name)

    def _methodptr_visit(self, value, name):
        self.visit(value.cast(self.long_type), name)

    def _common_generator(self, gen, typename):
        self.visit_string(gdb.Value(typename), '.type')
        if hasattr(gen, 'error'):    return self.visit(gdb.Value(True),    '.python_error')
        if hasattr(gen, 'size'):     self.visit(gdb.Value(gen.size()),     '.size')
        if hasattr(gen, 'capacity'): self.visit(gdb.Value(gen.capacity()), '.capacity')
        if hasattr(gen, 'buckets'):  self.visit(gdb.Value(gen.buckets()),  '.buckets')
        count = 0
        for elem in gen:
            self.visit(elem, '[%d]' % count)
            count += 1
            if count == self.n_elems_containers: break
