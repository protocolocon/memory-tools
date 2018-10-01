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

class MTmaps:
    """ reads and parses /proc/$pid/maps file """
    def __init__(self):
        self.regions = [] # [ [low, high, description] ]
        inferior = gdb.selected_inferior()
        if not inferior.pid: return # no inferior yet
        with open('/proc/%d/maps' % inferior.pid) as f:
            while not f.closed:
                line = f.readline()
                if not line: break
                line = line.split()
                low, high = [int(x, 16) for x in line[0].split('-')]
                # mmap (inode != 0)
                descr = (int(line[4]) or len(line) > 5) and line[5] or ''
                self.regions.append([low, high, descr])
        self.regions.sort()

        # find all stacks
        selected = gdb.selected_thread()
        for thread in inferior.threads():
            thread.switch()
            assert thread.is_valid()
            frame = gdb.newest_frame()
            assert thread.is_valid()
            region = self.get_region(frame.read_register('sp'))
            assert region
            region[2] = '[stack]'
        selected.switch() # leave original thread selected

    def dump(self, regions = None):
        print(c.white + 'regions' + c.reset)
        regions = regions or self.regions
        if not regions:
            print(c.red + '<empty>' + c.reset)
        else:
            print((c.cyan + '%16s %16s %10s %s' + c.reset) % ('Start', 'End', 'Size', 'Description'))
            for region in regions:
                print((c.green + '%16x %16x ' + c.yellow + '%10d ' + c.reset + '%s') %
                      (region[0], region[1], region[1] - region[0], region[2]))

    def get_region(self, address):
        for region in self.regions:
            if address >= region[0] and address < region[1]:
                return region
        return None

    def get_regions(self, names):
        regions = []
        for region in self.regions:
            descr = region[2]
            if descr:
                if (descr[0] == '[' and descr in names) or os.path.basename(descr) in names:
                    regions.append(region)
        return regions
