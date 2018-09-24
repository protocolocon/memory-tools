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

# Some of these class inspectors are based on libstdc++6 pretty printers:
#   /usr/share/gcc-8/python/libstdcxx/v6/printers.py

import gdb

def find_type(orig, name):
    type = orig.strip_typedefs()
    search = '%s::%s' % (type.unqualified(), name)
    return gdb.lookup_type(search)

def get_value_from_aligned_membuf(buf, valtype):
    """ Returns the value held in a __gnu_cxx::__aligned_membuf. """
    return buf['_M_storage'].address.cast(valtype.pointer()).dereference()


class MTarray:
    def __init__(self, value):
        self.value = value
        self.type_elem = value.type.target()

    @property
    def prop_type(self):
        return "array"

    @property
    def prop_size(self):
        return self.value.type.sizeof // self.type_elem.sizeof

    def get_item(self, i):
        return self.value[i]

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if self.iElem >= self.prop_size:
            raise StopIteration
        elem = self.get_item(self.iElem)
        self.iElem += 1
        return elem


class MTstd_vector:
    def __init__(self, value):
        self.value = value
        self.is_bool = value.type.template_argument(0).code  == gdb.TYPE_CODE_BOOL
        if not value.type.template_argument(0).sizeof:
            self.error = True

    @property
    def prop_type(self):
        return "std::vector"

    @property
    def prop_size(self):
        return self.value['_M_impl']['_M_finish'] - self.value['_M_impl']['_M_start']

    @property
    def prop_capacity(self):
        return self.value['_M_impl']['_M_end_of_storage'] - self.value['_M_impl']['_M_start']

    def get_item(self, i):
        start = self.value['_M_impl']['_M_start']
        start += i
        return start.dereference()

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if self.iElem >= self.prop_size:
            raise StopIteration
        elem = self.get_item(self.iElem)
        self.iElem += 1
        return elem


class MTstd_unordered_map:
    def __init__(self, value):
        self.value = value
        try:
            self.node = self.value['_M_h']['_M_before_begin']['_M_nxt']
        except:
            try:
                self.value['_M_h']['_M_bbegin']
            except:
                raise RuntimeError('unknown std::unordered_map implementation')
            else:
                raise RuntimeError('std::unordered map prior to libstdc++ 4.9')
        self.node_type = find_type(self.value['_M_h'].type, '__node_type').pointer()

    @property
    def prop_type(self):
        return "std::unordered_map"

    @property
    def prop_size(self):
        return self.value['_M_h']['_M_element_count']

    @property
    def prop_buckets(self):
        return self.value['_M_h']['_M_bucket_count']

    def __iter__(self):
        return self

    def __next__(self):
        if self.node == 0:
            raise StopIteration
        elem = self.node.cast(self.node_type).dereference()
        self.node = elem['_M_nxt']
        valptr = elem['_M_storage'].address
        valptr = valptr.cast(elem.type.template_argument(0).pointer())
        return valptr.dereference()


class MTstd_unordered_set(MTstd_unordered_map):
    @property
    def prop_type(self):
        return "std::unordered_set"


class MTstd_list:
    def __init__(self, value):
        self.value = value
        self.base = self.value['_M_impl']['_M_node']
        self.next = self.base['_M_next']
        self.type = find_type(self.value.type, 'value_type').pointer()
        self.nodeType = self.next.dereference().type.strip_typedefs().pointer()

    @property
    def prop_type(self):
        return "std::list"

    def __iter__(self):
        return self

    def __next__(self):
        if not self.next or self.next == self.base.address:
            raise StopIteration
        elem = self.next
        self.next = elem.dereference()['_M_next']
        node_ptr = elem.cast(self.nodeType)
        node = node_ptr.dereference()
        try:    # c++03
            return node['_M_storage'].address.cast(self.type).dereference()
        except: # c++11
            return (node_ptr + 1).cast(self.type).dereference()


class MTstd_deque:
    def __init__(self, value):
        self.value = value
        item_type = value.type.template_argument(0)
        size = item_type.sizeof
        if size < 512:
            self.buffer_size = int (512 / size)
        else:
            self.buffer_size = 1

    @property
    def prop_type(self):
        return "std::deque"

    @property
    def prop_size(self):
        start = self.value['_M_impl']['_M_start']
        end = self.value['_M_impl']['_M_finish']
        delta_n = end['_M_node'] - start['_M_node'] - 1
        delta_s = start['_M_last'] - start['_M_cur']
        delta_e = end['_M_cur'] - end['_M_first']
        return self.buffer_size * delta_n + delta_s + delta_e

    @property
    def prop_buckets(self):
        start = self.value['_M_impl']['_M_start']
        end = self.value['_M_impl']['_M_finish']
        return end['_M_node'] - start['_M_node'] + 1

    def __iter__(self):
        start = self.value['_M_impl']['_M_start']
        end = self.value['_M_impl']['_M_finish']
        self.node = start['_M_node']
        self.start = start['_M_cur']
        self.end = start['_M_last']
        self.last = end['_M_cur']
        return self

    def __next__(self):
        if self.start == self.last:
            raise StopIteration

        result = self.start.dereference()

        # advance the 'cur' pointer
        self.start = self.start + 1
        if self.start == self.end:
            # if we got to the end of this bucket, move to the next bucket
            self.node = self.node + 1
            self.start = self.node[0]
            self.end = self.start + self.buffer_size

        return result


class MTstd_map:
    def __init__(self, value):
        self.value = value
        self.size = value['_M_t']['_M_impl']['_M_node_count']

    @property
    def prop_type(self):
        return "std::map"

    @property
    def prop_size(self):
        return self.size

    def __iter__(self):
        self.count = 0
        self.node = self.value['_M_t']['_M_impl']['_M_header']['_M_left']
        rep_type = find_type(self.value.type, '_Rep_type')
        node = find_type(rep_type, '_Link_type')
        self.type = node.strip_typedefs()
        print("------", str(self.type))
        return self

    def _get_value_from_Rb_tree_node(self, node):
        """ returns the value held in an _Rb_tree_node<_Val> """
        try:
            member = node.type.fields()[1].name
            if member == '_M_value_field':
                # C++03 implementation, node contains the value as a member
                return node['_M_value_field']
            elif member == '_M_storage':
                # C++11 implementation, node stores value in __aligned_membuf
                valtype = node.type.template_argument(0)
                return get_value_from_aligned_membuf(node['_M_storage'], valtype)
        except:
            pass
        raise ValueError("Unsupported implementation for %s" % str(node.type))

    def __next__(self):
        if self.count == self.size:
            raise StopIteration
        result = self.node
        self.count = self.count + 1
        if self.count < self.size:
            # compute the next node
            node = self.node
            if node.dereference()['_M_right']:
                node = node.dereference()['_M_right']
                while node.dereference()['_M_left']:
                    node = node.dereference()['_M_left']
            else:
                parent = node.dereference()['_M_parent']
                while node == parent.dereference()['_M_right']:
                    node = parent
                    parent = parent.dereference()['_M_parent']
                if node.dereference()['_M_right'] != parent:
                    node = parent
            self.node = node
        return self._get_value_from_Rb_tree_node(result.cast(self.type).dereference())


class MTstd_set(MTstd_map):
    @property
    def prop_type(self):
        return "std::set"


class MTstd_unique_ptr:
    def __init__(self, value):
        self.value = value

    @property
    def prop_type(self):
        return "std::unique_ptr"

    def _get(self):
        try:    return self.value['_M_t']['_M_t']['_M_head_impl']
        except: pass

        try:    return self.value['_M_t']['_M_head_impl']
        except: pass

        raise 'std::unique_pointer: cannot access implementation'

    @property
    def prop_valid(self):
        v = self._get()
        return bool(int(v))

    def get_item(self):
        return self._get().dereference()

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if not self.iElem and self.prop_valid:
            self.iElem += 1
            return self.get_item()
        raise StopIteration


class MTstd_shared_ptr:
    def __init__(self, value):
        self.value = value

    @property
    def prop_type(self):
        return "std::shared_ptr"

    @property
    def prop_valid(self):
        v = self.value['_M_ptr']
        return int(v)

    def get_item(self):
        return self.value['_M_ptr'].dereference()

    @property
    def prop_ref_count(self):
        rc = self.value['_M_refcount']['_M_pi']
        return rc and rc['_M_use_count'] or 0

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if not self.iElem and self.prop_valid:
            self.iElem += 1
            return self.get_item()
        raise StopIteration


class MTstd_string:
    def __init__(self, value):
        self.value = value

    @property
    def prop_type(self):
        return "std::string"

    def get_item(self):
        data = self.value['_M_dataplus']['_M_p']
        data = data.cast(data.type.strip_typedefs())
        try:
            size = int(self.value['_M_string_length'])
        except:
            # size is two longs before
            size = int((data - data.type.sizeof * 2).cast(gdb.lookup_type('long').pointer()).dereference())
            assert size >= 0, "internal string"
        if int(data.cast(gdb.lookup_type('long'))): # not null
            value = data.dereference().cast(gdb.lookup_type('char').array(size - 1)) # return char[size] type
        else:
            value = gdb.Value(0).cast(gdb.lookup_type('char').pointer()) # return (char*)nullptr
        return value

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if not self.iElem:
            self.iElem += 1
            return self.get_item()
        raise StopIteration


class MTstd_mutex:
    def __init__(self, value):
        self.value = value

    @property
    def prop_type(self):
        return "std::mutex"

    @property
    def prop_locked(self):
        return bool(self.value['_M_mutex']['__data']['__lock'])

    @property
    def prop_owner(self):
        return int(self.value['_M_mutex']['__data']['__owner'])

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration


class MTstd_function:
    def __init__(self, value):
        self.value = value

    @property
    def prop_type(self):
        return "std::function"

    @property
    def prop_empty(self):
        return not bool(self.value['_M_functor']['_M_unused']['_M_object'])

    @property
    def prop_address(self):
        return int(self.value['_M_functor']['_M_unused']['_M_object'])

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if not self.iElem:
            self.iElem += 1
            return gdb.Value(self.prop_address)
        raise StopIteration


class MTframe_lf_chunk:
    def __init__(self, value):
        self.value = value['chunk']
        assert self.value.type.code == gdb.TYPE_CODE_PTR
        directory = int(self.value.cast(gdb.lookup_type('uint64_t')))
        self.initialized = directory != 0
        if self.initialized:
            directory = directory & -32
            self.directory = gdb.Value(directory).cast(gdb.lookup_type('uint64_t').pointer())

    @property
    def prop_type(self):
        return "frame::lf::Chunk"

    @property
    def prop_size(self):
        return self.initialized and int(self.directory[2]) - int(self.directory[0]) or 0

    @property
    def prop_capacity(self):
        return self.initialized and int(self.directory[1]) - int(self.directory[0]) or 0

    @property
    def prop_collected(self):
        return self.initialized and bool((int(self.value.cast(gdb.lookup_type('uint64_t'))) & 15) != 0) or False

    @property
    def prop_begin(self, type):
        return self.directory[0].cast(type.pointer())

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration


class MTframe_lf_vector:
    def __init__(self, value):
        self.value = value
        self.chunk = FrameLFChunk(value['chunk'])
        self.type = find_type(self.value.type, 'value_type').strip_typedefs()

    @property
    def prop_type(self):
        return "frame::lf::Vector"

    @property
    def prop_size(self):
        return self.chunk.prop_size // self.type.sizeof

    @property
    def prop_capacity(self):
        return self.chunk.prop_capacity // self.type.sizeof

    def get_item(self, i):
        return self.chunk.begin(self.type)[i]

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if self.iElem >= self.prop_size:
            raise StopIteration
        elem = self.get_item(self.iElem)
        self.iElem += 1
        return elem


class MTframe_lf_hashmap:
    def __init__(self, value):
        self.value = value
        self.bucketVector = FrameLFVector(value['buckets_'])

    @property
    def prop_type(self):
        return "frame::lf::HashMap"

    @property
    def prop_size(self):
        return self.value['size_']

    @property
    def prop_buckets(self):
        return self.bucketVector.prop_size

    def __iter__(self):
        self.iBucket = self.prop_buckets
        self.iNext = 0
        return self

    def __next__(self):
        if self.iBucket < 0: raise StopIteration

        if self.iNext and self.bucketVector.get_item(self.iNext)['free']:
            self.iNext = self.bucketVector.get_item(self.iNext)['free']
            return self.bucketVector.get_item(self.iNext)['kv']
        else:
            self.iBucket -= 1
            while self.iBucket >= 0:
                bucket = self.bucketVector.get_item(self.iBucket)
                if int(bucket['next']):
                    self.iNext = int(bucket['next'])
                    return self.bucketVector.get_item(self.iNext)['kv']
                self.iBucket -= 1
            raise StopIteration


class MTframe_hashmap_close_addressing:
    def __init__(self, value):
        self.value = value
        self.bucketVector = StdVector(value['buckets_'])

    @property
    def prop_type(self):
        return "frame::lf::HashMapCloseAddressing"

    @property
    def prop_size(self):
        return self.value['size_']

    @property
    def prop_buckets(self):
        return self.bucketVector.prop_size

    def __iter__(self):
        self.iBucket = self.prop_buckets
        self.iNext = 0
        return self

    def __next__(self):
        if self.iBucket < 0: raise StopIteration

        if self.iNext and self.bucketVector.get_item(self.iNext)['free']:
            self.iNext = self.bucketVector.get_item(self.iNext)['free']
            return self.bucketVector.get_item(self.iNext)['kv']
        else:
            self.iBucket -= 1
            while self.iBucket >= 0:
                bucket = self.bucketVector.get_item(self.iBucket)
                if int(bucket['next']):
                    self.iNext = int(bucket['next'])
                    return self.bucketVector.get_item(self.iNext)['kv']
                self.iBucket -= 1
            raise StopIteration
