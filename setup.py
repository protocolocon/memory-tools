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

import os, test.colors as c, errno

header = '# memory-tools initialization'
initialization = """
python
import sys
sys.path.append('%s')
import mt_init
end
"""

def add_initialization_code(filename):
    memory_tools_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    print('appending; memory-tools at ' + c.CYAN + memory_tools_dir + c.RESET)
    try:
        with open(filename, 'a') as f:
            f.write('\n' + header + initialization % memory_tools_dir)
    except IOError as ex:
        print(c.RED + 'error: ' + c.RESET + ex[1])
        return
    print(c.GREEN + 'success' + c.RESET)

if __name__ == "__main__":
    filename = os.path.expanduser('~') + '/.gdbinit'
    print('checking ' + c.CYAN + filename + c.RESET + ' for initialization of memory-tools in GDB')
    append = False
    try:
        with open(filename, 'r') as f:
            lines = f.read().split('\n')
            if not header in lines: append = True
    except IOError as ex:
        if ex[0] == errno.ENOENT:
            # file not found
            append = True

    if append:
        # append initialization code
        add_initialization_code(filename)
    else:
        print(c.GREEN + 'already set' + c.RESET)
