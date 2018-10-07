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

import gdb, os
from mt_colors import mt_colors as c

class MTobjects:
    """Find objects and relate their debug objects"""
    def __init__(self):
        class Objfile:
            def __init__(self, obj):
                self._obj = obj      # gdb.Objfile
                self._debug = set()  # { gdb.Objfile }
        class Progspace:
            def __init__(self, progspace):
                self._progspace = progspace
                self._objs = { }  # { obj.filename: Objfile }

        self._progspaces = { }    # { progpsace.filename: Progspace

        # get all main objects
        for obj in gdb.objfiles():
            if obj.is_valid() and obj.owner == None:
                assert obj.progspace.filename
                self._progspaces.setdefault(obj.progspace.filename, Progspace(obj))._objs[obj.filename] = Objfile(obj)
        # add separate debug objects
        for obj in gdb.objfiles():
            if obj.is_valid() and obj.owner != None:
                assert obj.progspace.filename and obj.progspace.filename in self._progspaces.keys()
                progspace = self._progspaces.get(obj.progspace.filename)
                assert obj.owner.filename in progspace._objs.keys()
                objfile = progspace._objs[obj.owner.filename]
                objfile._debug.add(obj)

    def dump(self):
        print(c.white + 'objects' + c.reset)
        for name, progspace in self._progspaces.items():
            print('  ' + c.cyan + os.path.basename(name) + ' ' + c.blue + os.path.dirname(name) + c.reset)
            for name_obj, objfile in progspace._objs.items():
                print('    ' + c.green + os.path.basename(name_obj) + ' ' + c.blue + os.path.dirname(name_obj) + c.reset)
                for debug_objfile in objfile._debug:
                    name_dbg = debug_objfile.filename
                    print('      ' + c.red + os.path.basename(name_dbg) + ' ' + c.blue + os.path.dirname(name_dbg) + c.reset)
