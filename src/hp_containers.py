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

def find_type(orig, name):
    type = orig.strip_typedefs()
    search = '%s::%s' % (type.unqualified(), name)
    return gdb.lookup_type(search)

class Array:
    def __init__(self, value):
        self.value = value
        self.type_elem = value.type.target()

    def size(self):
        return self.value.type.sizeof // self.type_elem.sizeof

    def get_elem(self, i):
        return self.value[i]

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if self.iElem >= self.size():
            raise StopIteration
        elem = self.get_elem(self.iElem)
        self.iElem += 1
        return elem


class StdVector:
    def __init__(self, value):
        self.value = value
        self.is_bool = value.type.template_argument(0).code  == gdb.TYPE_CODE_BOOL
        if not value.type.template_argument(0).sizeof:
            self.error = True

    def size(self):
        return self.value['_M_impl']['_M_finish'] - self.value['_M_impl']['_M_start']

    def capacity(self):
        return self.value['_M_impl']['_M_end_of_storage'] - self.value['_M_impl']['_M_start']

    def get_elem(self, i):
        start = self.value['_M_impl']['_M_start']
        start += i
        return start.dereference()

    def __iter__(self):
        self.iElem = 0
        return self

    def __next__(self):
        if self.iElem >= self.size():
            raise StopIteration
        elem = self.get_elem(self.iElem)
        self.iElem += 1
        return elem


class StdUnorderedMap:
    def __init__(self, value):
        self.value = value
        self.node = self.value['_M_h']['_M_before_begin']['_M_nxt']
        self.node_type = find_type(self.value['_M_h'].type, '__node_type').pointer()

    def size(self):
        return self.value['_M_h']['_M_element_count']

    def buckets(self):
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

class StdList:
    def __init__(self, value):
        self.value = value
        self.base = self.value['_M_impl']['_M_node']
        self.next = self.base['_M_next']
        self.type = find_type(self.value.type, 'value_type').pointer()
        self.nodeType = self.next.dereference().type.strip_typedefs().pointer()

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

class StdUniquePtr:
    def __init__(self, value):
        self.value = value

    def _get(self):
        try:    return self.value['_M_t']['_M_t']['_M_head_impl']
        except: pass

        try:    return self.value['_M_t']['_M_head_impl']
        except: pass

        raise 'std::unique_pointer: cannot access implementation'

    def valid(self):
        v = self._get()
        return int(v)

    def get_elem(self):
        return self._get().dereference()

class StdSharedPtr:
    def __init__(self, value):
        self.value = value

    def valid(self):
        v = self.value['_M_ptr']
        return int(v)

    def get_elem(self):
        return self.value['_M_ptr'].dereference()

    def ref_count(self):
        rc = self.value['_M_refcount']['_M_pi']
        return rc and rc['_M_use_count'] or 0

class StdString:
    def __init__(self, value):
        self.value = value

    def get(self):
        data = self.value['_M_dataplus']['_M_p']
        data = data.cast(data.type.strip_typedefs())
        try:
            size = self.value['_M_string_length']
        except:
            # size is two longs before
            size = int((data - data.type.sizeof * 2).cast(gdb.lookup_type('long').pointer()).dereference())
            assert size >= 0, "internal string"
        return data.string(length = size)

class StdMutex:
    def __init__(self, value):
        self.value = value

    def locked(self):
        return bool(self.value['_M_mutex']['__data']['__lock'])

    def owner(self):
        return int(self.value['_M_mutex']['__data']['__owner'])

class StdFunction:
    def __init__(self, value):
        self.value = value

    def empty(self):
        return not bool(self.value['_M_functor']['_M_unused']['_M_object'])

    def address(self):
        return int(self.value['_M_functor']['_M_unused']['_M_object'])

class FrameLFChunk:
    def __init__(self, value):
        self.value = value['chunk']
        assert self.value.type.code == gdb.TYPE_CODE_PTR
        directory = int(self.value.cast(gdb.lookup_type('uint64_t')))
        self.initialized = directory != 0
        if self.initialized:
            directory = directory & -32
            self.directory = gdb.Value(directory).cast(gdb.lookup_type('uint64_t').pointer())

    def size(self):
        return self.initialized and int(self.directory[2]) - int(self.directory[0]) or 0

    def capacity(self):
        return self.initialized and int(self.directory[1]) - int(self.directory[0]) or 0

    def collected(self):
        return self.initialized and bool((int(self.value.cast(gdb.lookup_type('uint64_t'))) & 15) != 0) or False

    def begin(self, type):
        return self.directory[0].cast(type.pointer())

class FrameLFVector:
    def __init__(self, value):
        self.value = value
        self.chunk = FrameLFChunk(value['chunk'])
        self.type = find_type(self.value.type, 'value_type').strip_typedefs()

    def size(self):
        return self.chunk.size() // self.type.sizeof

    def capacity(self):
        return self.chunk.capacity() // self.type.sizeof

    def get_elem(self, i):
        return self.chunk.begin(self.type)[i]

class FrameLFHashMap:
    def __init__(self, value):
        self.value = value
        self.bucketVector = FrameLFVector(value['buckets_'])
        self.iBucket = self.buckets()
        self.iNext = 0

    def size(self):
        return self.value['size_']

    def buckets(self):
        return self.bucketVector.size()

    def __iter__(self):
        return self

    def __next__(self):
        if self.iBucket < 0: raise StopIteration

        if self.iNext and self.bucketVector.get_elem(self.iNext)['free']:
            self.iNext = self.bucketVector.get_elem(self.iNext)['free']
            return self.bucketVector.get_elem(self.iNext)['kv']
        else:
            self.iBucket -= 1
            while self.iBucket >= 0:
                bucket = self.bucketVector.get_elem(self.iBucket)
                if int(bucket['next']):
                    self.iNext = int(bucket['next'])
                    return self.bucketVector.get_elem(self.iNext)['kv']
                self.iBucket -= 1
            raise StopIteration

class FrameHashMapCloseAddressing:
    def __init__(self, value):
        self.value = value
        self.bucketVector = StdVector(value['buckets_'])
        self.iBucket = self.buckets()
        self.iNext = 0

    def size(self):
        return self.value['size_']

    def buckets(self):
        return self.bucketVector.size()

    def __iter__(self):
        return self

    def __next__(self):
        if self.iBucket < 0: raise StopIteration

        if self.iNext and self.bucketVector.get_elem(self.iNext)['free']:
            self.iNext = self.bucketVector.get_elem(self.iNext)['free']
            return self.bucketVector.get_elem(self.iNext)['kv']
        else:
            self.iBucket -= 1
            while self.iBucket >= 0:
                bucket = self.bucketVector.get_elem(self.iBucket)
                if int(bucket['next']):
                    self.iNext = int(bucket['next'])
                    return self.bucketVector.get_elem(self.iNext)['kv']
                self.iBucket -= 1
            raise StopIteration
