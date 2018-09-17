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

class_template_params = {
    'std::vector':         1,
    'std::map':            2,
    'std::set':            1,
    'std::unordered_map':  2,
    'std::unordered_set':  1,
    'std::__cxx11::list':  1,
    'std::unique_ptr':     1,
    'std::shared_ptr':     1,
    'frame::lf::HashMap':  2,
    'frame::lf::Vector':   1,
}

def remove_template_params(string):
    template = string.find('<')
    if template < 0: return string # no templates
    return string[:template] + string[string.rfind('>') + 1:]

def clean_template_arguments(string, num):
    level = 0
    new = ''
    last = 0
    for i, c in enumerate(string):
        if c == '<': level += 1
        elif c == '>': level -= 1
        elif c == ',' and not level:
            # template argument
            if not num: break
            num -= 1
            if last: new += ', '
            new += remove_template_params(string[last:i])
            last = i + 2
    if num:
        if last: new += ', '
        new += remove_template_params(string[last:])
    return new

def clean_type_name(typename):
    if not typename: return ''
    level = 0
    new = ''
    last = 0
    for i, c in enumerate(typename):
        if c == '<':
            if not level:
                new += typename[last:i]
                last = i
            level += 1
        elif c == '>':
            level -= 1
            if not level:
                if i + 1 >= len(typename):
                    num_args = class_template_params.get(typename[:last], 3)
                    new += '<' + clean_template_arguments(typename[last + 1:i], num_args) + '>'
                last = i + 1
    new += typename[last:]
    return new

def clean_type(type):
    return clean_type_name(str(type))

    """ this code does similar to str(type) """
    """
    prefix = ''
    type_name = ''
    deref = ''
    if type.const() == type: prefix = 'const '
    if type.volatile() == type: prefix = 'volatile '
    while type.name == None:
        if type.code == gdb.TYPE_CODE_PTR:
            type = type.target()
            deref += '*'
        elif type.code == gdb.TYPE_CODE_ARRAY:
            type = type.target()
            deref += '[]'
        elif type.code == gdb.TYPE_CODE_REF:
            type = type.target()
            deref += '&'
        elif type.code == gdb.TYPE_CODE_STRUCT:
            prefix += 'struct '
            break
        elif type.code == gdb.TYPE_CODE_UNION:
            prefix += 'union '
            break
        elif type.code == gdb.TYPE_CODE_ENUM:
            prefix += 'enum '
            break
        elif type.code == gdb.TYPE_CODE_FUNC:
            type_name = clean_type(type.target()) + ' (' + deref + ')()'
            deref = ''
            break
        else:
            break
    return clean_type_name(prefix + (type.name or type.tag or type_name or '?') + deref)
    """
