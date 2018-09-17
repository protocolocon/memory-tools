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

import sys, os, re, test.colors as c, subprocess

def follow_links(binary):
    while os.path.islink(binary):
        binary = os.path.join(os.path.dirname(binary), os.readlink(binary))
    return binary

def find_binaries(regex):
    """ find unique binaries following filename pattern regex """
    binaries = set()
    bin_list = []
    for path in os.environ["PATH"].split(os.pathsep):
        for f in os.listdir(path):
            fabs = os.path.join(path, f)
            if re.match(regex, f) and os.access(fabs, os.X_OK):
                final = follow_links(fabs)
                if final not in binaries:
                    binaries.add(final)
                    bin_list.append(fabs)
    bin_list.sort()
    return bin_list

def cout(string):
    sys.stdout.write(string)
    sys.stdout.flush()

def profile_uut(pid):
    commands_file = 'test/gdb_commands.txt'
    gdbs = find_binaries('^gdb(\-\d+[\.\d+]*)?$')
    debug = sys.argv.count('debug')
    tests = []
    for arg in sys.argv[1:]:
        if arg.startswith('test_'):
            tests.append(arg)

    for gdb in gdbs:
        args = [gdb, '-p', str(pid),
                '-ex', 'python debug_uut = ' + str(debug),
                '-ex', 'python tests_uut = ' + str(tests),
                '-x', commands_file, '-q']
        if debug: # do not redirect in, out, err
            popen = subprocess.Popen(args)
        else:
            popen = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            out = popen.stdout.read().decode("utf-8")
            for match in re.findall('@-@[^@]*@-@', out): cout(match[3:-3])
        if popen.wait():
            cout(c.RED + 'g')
        else:
            cout(c.GREEN + 'g')

def execute_uut(binary):
    popen = subprocess.Popen([binary], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out = popen.stdout.read()

    if not out or out != b'ready':
        cout(c.RED + 'x')
    else:
        cout(c.GREEN + 'x')
        # heap profile live process
        profile_uut(popen.pid)
        # tell process to finish
        popen.communicate(b'exit')
        popen.wait()

def check_compiler(compiler, prefixes):
    compiler = os.path.basename(compiler)
    if not prefixes: return True
    for prefix in prefixes:
        if compiler.startswith(prefix):
            return True
    return False

def compile_uut(compiler_prefixes, cpp_stds, compile_optims):
    # use all possible compilers available in the system
    binary = 'test/uut'
    source = 'test/uut.cc'
    compilers = find_binaries('^g\+\+(\-\d+[\.\d+]*)?$') + find_binaries('^clang\+\+(\-\d+[\.\d+]*)?$')
    if not len(compilers):
        print(c.BROWN + "warning: no C++ compilers found" + c.RESET)
    for compiler in compilers:
        if not check_compiler(compiler, compiler_prefixes): continue
        cout(('%-20s' + c.RESET) % os.path.basename(compiler))
        for cpp_std in cpp_stds:
            cout(c.CYAN + cpp_std[-2:])
            for compile_optim in compile_optims:
                # compile UUT
                args = [compiler] + compile_optim + ['-g', '-Wall', '-Werror', cpp_std, '-o', binary, source, '-pthread']
                popen = subprocess.Popen(args, stderr = subprocess.PIPE)
                if popen.wait():
                    cout(c.RED + "c")
                else:
                    cout(c.BLUE + "c")
                    execute_uut(binary)

        cout(c.RESET + '\n')

def main():
    # change directory to base of heap profile project (allows executing test from any directory)
    os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

    python_versions_mark = 'lock-python'
    if not sys.argv.count(python_versions_mark):
        # try with different python versions
        python_exes = find_binaries('^python(\d+[\.\d+]*)?[dmu]?$')

        # execute this test with different python interpreters
        print(c.WHITE + "Heap Profiler: " + c.RESET + "self test")
        args = sys.argv
        args[0] = os.path.basename(args[0])
        for python in python_exes:
            print(c.YELLOW + os.path.basename(python) + c.RESET)
            popen = subprocess.Popen([python] + args + [python_versions_mark])
            if popen.wait():
                print(c.RED + "finished with error for " + os.path.basename(python) + c.RESET)
    else:
        # check override options
        cpp_stds = []
        compile_optims = []
        compiler_prefixes = []
        for arg in sys.argv[1:]:
            if arg.startswith('-std='):
                cpp_stds.append(arg)
            elif arg.startswith('-'):
                compile_optims.append(arg.split())
            elif arg.startswith('test_'):
                pass
            elif arg not in ['lock-python', 'debug']:
                compiler_prefixes.append(arg)
        cpp_stds = cpp_stds or ['-std=c++03', '-std=c++11', '-std=c++14', '-std=c++17']
        compile_optims = compile_optims or [['-O0', '-m64'], ['-O2', '-m64'], ['-O0', '-m32']]

        compile_uut(compiler_prefixes, cpp_stds, compile_optims)
