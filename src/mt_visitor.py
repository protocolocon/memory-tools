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
from mt_containers import (MTarray, MTstd_vector, MTstd_unordered_map, MTstd_unordered_set,
                           MTstd_unique_ptr, MTstd_shared_ptr, MTstd_string, MTstd_mutex,
                           MTstd_list, MTstd_function, MTstd_deque, MTstd_map, MTstd_set,
                           MTframe_lf_hashmap, MTframe_lf_vector, MTframe_lf_chunk,
                           MTframe_hashmap_close_addressing)

mt_type_code_to_name = {
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
        func_name = 'visit_' + mt_type_code_to_name.get(code, 'unhandled')
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
            print('missing type code:', mt_type_code_to_name[value.type.code])

        visitors.get(value.type.code, unhandled)(value, name)

    def get_struct_wrapper(self, value):
        """ provided a value, return the wrapping object around the structure or None"""
        if value.type.code == gdb.TYPE_CODE_ARRAY: return MTarray(value)
        if value.type.code != gdb.TYPE_CODE_STRUCT or not value.type.name: return None
        typename = value.type.name
        # C++ standard library
        if typename.startswith('std::'):
            if typename.startswith('std::vector<'): return MTstd_vector(value)
            elif typename.startswith('std::unordered_map<'): return MTstd_unordered_map(value)
            elif typename.startswith('std::unordered_set<'): return MTstd_unordered_set(value)
            elif typename.startswith('std::unique_ptr<'): return MTstd_unique_ptr(value)
            elif typename.startswith('std::shared_ptr<'): return MTstd_shared_ptr(value)
            elif typename.startswith('std::__cxx11::basic_string<') or typename.startswith('std::basic_string<'):
                return MTstd_string(value)
            elif typename == 'std::mutex' or typename == 'std::recursive_mutex': return MTstd_mutex(value)
            elif typename.startswith('std::__cxx11::list<') or typename.startswith('std::list<'):
                return MTstd_list(value)
            elif typename.startswith('std::function<'): return MTstd_function(value)
            elif typename.startswith('std::deque<'): return MTstd_deque(value)
            elif typename.startswith('std::map<'): return MTstd_map(value)
            elif typename.startswith('std::set<'): return MTstd_set(value)

        # boost
        elif typename.startswith('boost::'):
            if typename.startswith('boost::multi_index::multi_index_container<'):
                return # TODO

        # lock free
        elif typename.startswith('frame::'):
            if typename.startswith('frame::lf::HashMap<') and typename[-1] == '>': return MTframe_lf_hashmap(value)
            elif typename.startswith('frame::HashMapCloseAddressing<') and typename[-1] == '>':
                return MTframe_hashmap_close_addressing(value)
            elif typename.startswith('frame::lf::Vector<'): return MTframe_lf_vector(value)
            elif typename == 'frame::lf::Chunk': return MTframe_lf_chunk

    def is_string_const_char(self, value):
        if value.type.code != gdb.TYPE_CODE_PTR: return False
        base_type = value.type.target()
        return base_type.name == 'char' and base_type == base_type.const()

    def is_string_char_array(self, value):
        if value.type.code != gdb.TYPE_CODE_ARRAY: return False
        return value.type.target().name == 'char'

    def is_string(self, value):
        return self.is_string_const_char() or self.is_string_char_array()

    def _struct_visit(self, value, name):
        # well known class / struct
        wrap = self.get_struct_wrapper(value)
        if wrap: return self._manage_wrap(wrap, name)

        # unknown class / struct
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
                # there is a problem with references in which correct addresses are not correctly provided by gdb
                # convert references to pointers inferring address (cast would also take bad address)
                new_value = value[field_name]
                if new_value.type.code == gdb.TYPE_CODE_REF:
                    assert not (int(field.bitpos) & 3) # reference in a bitfield?
                    address = int(value.address) + (field.bitpos >> 3)
                    # if Value = T&, convert to Value = *((T**)address)
                    new_value = gdb.Value(address).cast(new_value.type.target().pointer().pointer()).dereference()
                self.visit(new_value, field_name or '<anonymous>')
            else:
                # static member
                pass #print('missing static member')

    def _union_visit(self, value, name):
        for field_name, field in value.type.items():
            #print('Union:', name, field_name, field.type.code, field.type.name)
            self.visit(value[field_name], '+' + (field_name or '<anonymous>'))

    def _array_visit(self, value, name):
        array = MTarray(value)
        # special case, array of char -> string
        if array.type_elem.name == 'char':
            self.visit_string(value, name)
            return
        return self._manage_wrap(array, name)

    def _ptr_visit(self, value, name):
        # special case 'const char *'
        base_type = value.type.target()
        if base_type.name == 'char' and base_type == base_type.const():
            self.visit_string(value, name)
            return

        try:
            value = value.dereference()     # could fail if generic pointer
            str(value.cast(self.char_type)) # test that values is in accessible memory
        except:
            #self.visit(value.cast(self.long_type), name) # visit with the pointer value
            return
        self.visit(value, '*' + name)

    def _ref_visit(self, value, name):
        self.visit(value.referenced_value(), '&' + name)

    def _typedef_visit(self, value, name):
        self.visit(value.cast(value.type.strip_typedefs()), name)

    def _func_visit(self, value, name):
        self.visit(value.cast(self.long_type), name)

    def _methodptr_visit(self, value, name):
        self.visit(value.cast(self.long_type), name)

    def _manage_wrap(self, wrap, name):
        # add properties
        for prop in [prop for prop in dir(wrap) if prop.startswith('prop_')]:
            prop_value = getattr(wrap, prop)
            if isinstance(prop_value, str):
                self.visit_string(gdb.Value(prop_value), '.' + prop[5:])
            else:
                self.visit(gdb.Value(prop_value), '.' + prop[5:])

        # items
        count = 0
        for item in wrap:
            self.visit(item, ('[%d]' + name) % count)
            count += 1
            if count == self.n_elems_containers: break
