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

import gdb, os, mt_util
from mt_colors import mt_colors as c

mt_map_types = {
    0x0001:   ('heap',     'h'),
    0x0002:   ('stack',    's'),
    0x0004:   ('vdso',     'V'),
    0x0008:   ('vvar',     'v'),
    0x0010:   ('info',     'i'),
    0x0020:   ('text',     't'),
    0x0040:   ('rodata',   'r'),
    0x0080:   ('data',     'd'),
    0x0100:   ('bss',      'b'),
    0x0200:   ('ini/fin',  '^'),
    0x0400:   ('plt',      'j'),   # procedure linkage table
    0x0800:   ('eh',       'e'),   # exception handling
    0x1000:   ('dyn',      '@'),
    0x2000:   ('debug',    '_'),   # should not appear
    0x4000:   ('got',      'g'),   # global offset table
    0x8000:   ('unk',      '?'),   # elf section unknown
}

mt_map_codenames = {
    # provided by system
    '[heap]':    0x0001,
    '[stack]':   0x0002,
    '[vdso]':    0x0004,
    '[vvar]':    0x0008,

    # mt classification
    '[info]':    0x0010,
    '[text]':    0x0020,
    '[rodata]':  0x0040,
    '[data]':    0x0080,
    '[bss]':     0x0100,
    '[ini/fin]': 0x0200,
    '[plt]':     0x0400,
    '[eh]':      0x0800,
    '[dyn]':     0x1000,
    '[debug]':   0x2000,
    '[got]':     0x4000,
    '[unk]':     0x8000,
}

mt_elf_sections = {
    '.interp':            0x0010,
    '.note':              0x0010,
    '.note.ABI-tag':      0x0010,
    '.note.gnu.build-id': 0x0010,
    '.gnu.hash':          0x0010,
    '.hash':              0x0010,
    '.dynsym':            0x1000,
    '.dynstr':            0x1000,
    '.gnu.version':       0x0010,
    '.gnu.version_r':     0x0010,
    '.gnu.version_d':     0x0010,
    '.rela.dyn':          0x1000,
    '.rela.plt':          0x1000,
    '.init':              0x0200,
    '.plt':               0x0400,
    '.plt.got':           0x0400,
    '.text':              0x0020,
    '.fini':              0x0200,
    '.rodata':            0x0040,
    '.eh_frame_hdr':      0x0800,
    '.eh_frame':          0x0800,
    '.gcc_except_table':  0x0800,
    '.init_array':        0x0200,
    '.fini_array':        0x0200,
    '.data.rel.ro':       0x1000,
    '.dynamic':           0x1000,
    '.got':               0x4000,
    '.got.plt':           0x4000,
    '.data':              0x0080,
    '.tdata':             0x0080,  # thread local storage
    '.bss':               0x0100,
    '.tbss':              0x0100,  # thread local storage
    '.line':              0x2000,
    '.debug':             0x2000,
    '.comment':           0x2000,
    '.debug_aranges':     0x2000,
    '.debug_info':        0x2000,
    '.debug_abbrev':      0x2000,
    '.debug_line':        0x2000,
    '.debug_str':         0x2000,
    '.debug_loc':         0x2000,
    '.debug_ranges':      0x2000,
    '<unknown>':          0x8000,
}

class MTmaps:
    """ reads and parses /proc/$pid/maps file """
    class Region:
        def __init__(self, low, high, map_type, file_mmap, permission):
            self.low = low
            self.high = high
            self.map_type = map_type
            self.file_mmap = file_mmap
            self.permission = permission

        def __lt__(self, region):
            return self.low < region.low

        def build_description(self):
            desc = ''
            t = self.map_type
            i = 1
            while t:
                if t & 1:
                    desc += mt_map_types[i][0] + ' '
                t >>= 1
                i <<= 1
            if desc: desc = '[' + desc.strip() + ']'
            if self.file_mmap:
                desc += (desc and ' ' or '') + c.cyan + os.path.basename(self.file_mmap) + ' ' + c.blue + os.path.dirname(self.file_mmap) + c.reset
            return desc

    @mt_util.maintain_thread_frame
    def __init__(self, show_unknown = False):
        self.regions = [] # [ Region ]
        inferior = gdb.selected_inferior()
        if not inferior.pid: return # no inferior yet
        with open('/proc/%d/maps' % inferior.pid) as f:
            while not f.closed:
                line = f.readline()
                if not line: break
                line = line.split()
                low, high = [int(x, 16) for x in line[0].split('-')]
                # mmap (inode != 0)
                file_mmap = int(line[4]) and len(line) > 5 and line[5] or ''
                permission = line[1]
                # type
                map_type = 0
                if not int(line[4]) and len(line) > 5 and line[5].startswith('['):
                    assert line[5].endswith(']'), 'parsing'
                    if line[5] in mt_map_codenames.keys():
                        map_type |= mt_map_codenames[line[5]]
                self.regions.append(MTmaps.Region(low, high, map_type, file_mmap, permission))
        self.regions.sort()

        # find all stacks
        for thread in inferior.threads():
            thread.switch()
            assert thread.is_valid()
            frame = gdb.newest_frame()
            assert thread.is_valid()
            region = self.get_region(frame.read_register('sp'))
            assert region
            region.map_type |= mt_map_codenames['[stack]']

        # refine elf file mappings using gdb
        files = gdb.execute('info files', to_string = True)
        for line in files.split('\n'):
            parts = line.split()
            if len(parts) >= 5 and parts[1] == '-' and parts[3] == 'is':
                if parts[4] in mt_elf_sections.keys():
                    region = self.get_region(int(parts[0], 0))
                    assert region, 'internal'
                    region.map_type |= mt_elf_sections[parts[4]]
                    if not region.file_mmap and len(parts) >= 7: # complete file mapping
                        region.file_mmap = parts[-1]
                else:
                    if show_unknown:
                        print(c.red + 'unknown elf section type: ' + c.reset + parts[4] + ' ' + c.blue + os.path.basename(parts[6]) + c.reset)
                    region.map_type |= mt_elf_sections['<unknown>']

    def dump(self, regions = None):
        print(c.white + 'regions' + c.reset)
        regions = regions == None and self.regions or regions
        if not regions:
            print(c.red + '<empty>' + c.reset)
        else:
            print((c.cyan + '%16s %16s %10s %4s %s' + c.reset) % ('Start', 'End', 'Size', 'Perm', 'Description'))
            for region in regions:
                print((c.green + '%16x %16x ' + c.yellow + '%10d ' + c.reset + c.magenta + '%4s ' + c.reset + '%s') %
                      (region.low, region.high, region.high - region.low, region.permission, region.build_description()))

    def get_region(self, address):
        for region in self.regions:
            if address >= region.low and address < region.high:
                return region
        return None

    def get_regions(self, names):
        # convert [] names into map_type
        map_type = 0
        new_names = []
        for name in names:
            if name.startswith('['):
                if name in mt_map_codenames.keys():
                    map_type |= mt_map_codenames[name]
            else:
                new_names.append(name)
        names = set(new_names)

        regions = []
        for region in self.regions:
            if (map_type & region.map_type) or os.path.basename(region.file_mmap) in names:
                regions.append(region)
        return regions
