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

import sys, colors as c, hp_symbols, hp_to_python, hp_memory, hp_maps

# passed by through gdb_commands
debug_uut = False
tests_uut = []

def cout(string):
    """ synchronized output with parent via pipe """
    sys.stdout.write('@-@' + string + '@-@')


class Test:
    def __init__(self, symbols = None, func = None):
        self.symbols = symbols
        self.func = func
        self.run = func and (not tests_uut or func.__name__ in tests_uut)

    def test(self):
        if self.run: self.func(self, self.symbols)

    def __enter__(self):
        self._assertions = 0
        self._errors = 0
        self._failed = []
        return self

    def __exit__(self, type, value, traceback):
        if not self.run: return True

        if isinstance(value, Exception):
            cout(c.RED + 'e')
        elif self._errors:
            cout(c.RED + 't')
        elif not self._assertions:
            cout(c.BROWN + '!')
        else:
            cout(c.GREEN + '.')
        if debug_uut: # stop in gdb promp for debugging in case of error
            if self._errors:
                print('number of assertions:', self._assertions, 'number of errors:', self._errors, self._failed)
                raise RuntimeError('test failed')
        else:
            return True # supress exception

    def check(self, condition):
        self._assertions += 1
        if not condition:
            self._errors += 1
            self._failed.append(self._assertions)

def test_get_python(t, symbols, var_name):
    syms = symbols.find_symbol(var_name)
    t.check(len(syms) == 1)
    # convert to python
    python = hp_to_python.HPpython().get(syms[0])
    if debug_uut: print(str(python))
    return python

def test_class(t, python):
    t.check(python['i'] == 33)
    t.check(python['b'] == True)
    t.check(abs(python['f'] - 42.42) < 1e-5)
    t.check(abs(python['d'] + 42.42) < 1e-14)
    t.check(python['c'] == ord('f'))
    t.check(python['charp'] == 'hello world')
    t.check(python['cp'] == None)

def test_local_class(t, symbols):
    python = test_get_python(t, symbols, 'hp_lc')
    test_class(t, python)

def test_global_class(t, symbols):
    python = test_get_python(t, symbols, 'hp_gc')
    test_class(t, python)

def test_class_ptr(t, symbols):
    python = test_get_python(t, symbols, 'hp_gcp')
    t.check(python['cp'])
    t.check(python['charp'] == 'top')
    t.check(python['cp']['charp'] == 'bottom')

def test_class_ptr_loop(t, symbols):
    python = test_get_python(t, symbols, 'hp_gcpl')
    t.check(python['cp'])
    t.check(python['charp'] == 'class A')
    t.check(python['cp']['charp'] == 'class B')
    t.check(python['cp']['cp']['charp'] == 'class A')

def test_global_vector_int(t, symbols):
    python = test_get_python(t, symbols, 'hp_gvi')
    t.check(python['.type'] == 'std::vector')
    t.check(python['.size'] == 3)
    t.check(python[0] == 1)
    t.check(python[1] == 7)
    t.check(python[2] == -100)

def test_global_vector_class(t, symbols):
    python = test_get_python(t, symbols, 'hp_gvc')
    t.check(python['.type'] == 'std::vector')
    t.check(python['.size'] == 2)
    t.check(python[0]['i'] == 999)
    t.check(python[1]['i'] == 1001)

def test_global_unordered_map_int_int(t, symbols):
    python = test_get_python(t, symbols, 'hp_gumii')
    t.check(python['.type'] == 'std::unordered_map')
    t.check(python['.size'] == 3)
    d = { v['first']: v['second'] for k, v in python.items() if isinstance(k, int) }
    t.check(d[99] == -99)
    t.check(d[999] == -999)
    t.check(d[9999] == -9999)
    python = test_get_python(t, symbols, 'hp_gusi')
    t.check(python['.type'] == 'std::unordered_set')
    d = { v for k, v in python.items() if isinstance(k, int) }
    t.check(-9 in d)
    t.check(-91 in d)
    t.check(-99 not in d)

def test_global_list_int(t, symbols):
    python = test_get_python(t, symbols, 'hp_gli')
    t.check(python['.type'] == 'std::list')
    t.check(python[0] == 49)
    t.check(python[1] == 7)

def test_global_unique_ptr(t, symbols):
    python = test_get_python(t, symbols, 'hp_gupi')
    t.check(python['.type'] == 'std::unique_ptr')
    t.check(python['*'] == 66)
    python = test_get_python(t, symbols, 'hp_gupc')
    t.check(python['.type'] == 'std::unique_ptr')
    t.check(python['*']['charp'] == 'hello world')
    python = test_get_python(t, symbols, 'hp_gupc_null')
    t.check(python['.type'] == 'std::unique_ptr')
    t.check(not '*' in python.keys())

def test_global_shared_ptr(t, symbols):
    python = test_get_python(t, symbols, 'hp_gspi')
    t.check(python['.type'] == 'std::shared_ptr')
    t.check(python['*'] == 66)
    t.check(python['.ref_count'] == 1)
    python = test_get_python(t, symbols, 'hp_gspc')
    t.check(python['.type'] == 'std::shared_ptr')
    t.check(python['*']['charp'] == 'hello world')
    t.check(python['.ref_count'] == 1)
    python = test_get_python(t, symbols, 'hp_gspc_null')
    t.check(python['.type'] == 'std::shared_ptr')
    t.check(not '*' in python.keys())
    t.check(python['.ref_count'] == 0)

def test_global_string(t, symbols):
    python = test_get_python(t, symbols, 'hp_gstr')
    t.check(python['.type'] == 'std::string')
    t.check(python['*'] == "bye")
    python = test_get_python(t, symbols, 'hp_gstr_long')
    t.check(python['.type'] == 'std::string')
    t.check(python['*'] == "The quick brown fox jumps over the lazy dog multiple times to do this string longer...")

def test_mutex(t, symbols):
    python = test_get_python(t, symbols, 'hp_thread_mutex')
    t.check(python['.type'] == 'std::mutex')
    t.check(python['.locked'] == True)
    t.check(python['.owner'] >= 0)
    python = test_get_python(t, symbols, 'hp_tc')
    t.check(python['i'] == 33)
    t.check(python['charp'] == None)

def test_function(t, symbols):
    python = test_get_python(t, symbols, 'hp_gfunc')
    t.check(python['.type'] == 'std::function')
    t.check(python['*'] >= 0)

def test_global_array(t, symbols):
    python = test_get_python(t, symbols, 'hp_gaus')
    t.check(python['.type'] == 'array')
    t.check(python['.size'] == 8)
    t.check(python[0] == 4)
    t.check(python[2] == 2)
    t.check(python[6] == 6)
    t.check(python[7] == 5)
    python = test_get_python(t, symbols, 'hp_gaaul')
    t.check(python['.type'] == 'array')
    t.check(python['.size'] == 2)
    t.check(python[0]['.type'] == 'array')
    t.check(python[0]['.size'] == 3)
    t.check(python[0][0] == 1)
    t.check(python[0][1] == 2)
    t.check(python[0][2] == 3)
    t.check(python[1]['.type'] == 'array')
    t.check(python[1]['.size'] == 3)
    t.check(python[1][0] == 999999999999)
    t.check(python[1][1] == 888888888888)
    t.check(python[1][2] == 777777777777)

def test_global_union(t, symbols):
    python = test_get_python(t, symbols, 'hp_gunion')
    t.check(python['+i'] == 0)
    t.check(python['+charp'] == None)

def test_global_enum(t, symbols):
    python = test_get_python(t, symbols, 'hp_genum')
    t.check(python == 100)

def test_global_reference(t, symbols):
    python = test_get_python(t, symbols, 'hp_gcr')
    test_class(t, python['&ref'])

def test_global_inheritance(t, symbols):
    python = test_get_python(t, symbols, 'hp_gcd')
    test_class(t, python['.base']['.base'])
    t.check(python['.base']['i_deriv'] == 0)
    t.check(python['.base']['f_deriv'] == 0.0)


def test(debug, tests):
    global debug_uut
    global tests_uut
    debug_uut = debug
    tests_uut = tests

    """ this is called within gdb with UUT as inferior """
    symbols = hp_symbols.HPsymbols()
    # c++03 compatible tests
    with Test(symbols, test_local_class) as t: t.test()
    with Test(symbols, test_global_class) as t: t.test()
    with Test(symbols, test_class_ptr) as t: t.test()
    with Test(symbols, test_class_ptr_loop) as t: t.test()
    with Test(symbols, test_global_vector_int) as t: t.test()
    with Test(symbols, test_global_vector_class) as t: t.test()
    with Test(symbols, test_global_list_int) as t: t.test()
    with Test(symbols, test_global_string) as t: t.test()
    with Test(symbols, test_global_array) as t: t.test()
    with Test(symbols, test_global_union) as t: t.test()
    with Test(symbols, test_global_enum) as t: t.test()
    with Test(symbols, test_global_reference) as t: t.test()
    with Test(symbols, test_global_inheritance) as t: t.test()

    # c++11 compatible tests
    have_cpp11 = False
    with Test() as t:
        if test_get_python(t, symbols, "have_cpp11"):
            have_cpp11 = True

    if have_cpp11:
        with Test(symbols, test_global_unordered_map_int_int) as t: t.test()
        with Test(symbols, test_global_unique_ptr) as t: t.test()
        with Test(symbols, test_global_shared_ptr) as t: t.test()
        with Test(symbols, test_mutex) as t: t.test()
        with Test(symbols, test_function) as t: t.test()

    # test
    if False:
        symbol = symbols.find_symbol('hp_gaaul')[0][0]
        value0 = symbol.value()
        value1 = symbol.value()
        type0 = value0.type
        type1 = value1.type
        print(symbol, value0)
        print(value0 == value1, value0 is value1)
        print(type0 == type1, type0 is type1)
        print(dir(type0))
        print(type0.__str__(), type1.__str__())
        raise

    # test
    if False:
        maps = hp_maps.HPmaps()
        regions = maps.get_regions(['uut', '[stack]', '[heap]'])
        maps.dump(regions)
        filtered_symbols = symbols.filter_by_providers(['uut'])
        filtered_symbols.dump()
        print("total:", len(symbols.symbols), "filtered:", len(filtered_symbols.symbols))
        hp_memory.HPmemory().analysis(filtered_symbols)
        raise
