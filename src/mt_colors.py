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

class MTcolors:
    'Optionally use colors'
    def __init__(self):
        self.use_colors = True
        self._color_RED       = '\033[31m'
        self._color_GREEN     = '\033[32m'
        self._color_BROWN     = '\033[33m'
        self._color_BLUE      = '\033[34m'
        self._color_MAGENTA   = '\033[35m'
        self._color_CYAN      = '\033[36m'
        self._color_WHITE     = '\033[37m'
        self._color_RED_BOLD  = '\033[1;31m'
        self._color_BLUE_BOLD = '\033[1;34m'
        self._color_YELLOW    = '\033[1;33m'
        self.RESET            = '\033[0m'

    def use(self, argument, from_tty):
        if not argument:
            self.use_colors = not self.use_colors
            if from_tty: print(self.cyan + 'colors: ' + self.green + (self.use_colors and 'ON' or 'OFF') + self.reset)
        elif argument.lower() == 'on':
            self.use_colors = True
        elif argument.lower() == 'off':
            self.use_colors = False
        elif argument.lower() == 'list':
            print(self.white + 'colors' + self.reset)
            for attr in [x for x in dir(self) if x.startswith('_color_')]:
                print('  this color is: ' + getattr(self, attr) + attr[7:] + ' ' +
                      attr[7:].lower() + ' ' + self.RESET + attr[7:].lower())
        else:
            colors = { x[7:].lower(): x for x in dir(self) if x.startswith('_color_') }
            args = argument.split()
            args[0] = args[0].lower()
            if len(args) == 2 and args[0] in colors.keys():
                # configure color
                args[1] = bytes(args[1], 'utf8').decode('unicode_escape')
                if from_tty:
                    print('setting ' + args[0] + ' from ' + getattr(self, colors[args[0]]) + args[0] + self.RESET +
                          ' to ' + args[1] + args[0] + self.RESET)
                setattr(self, colors[args[0]], args[1])
            else:
                print(self.red + 'error: ' + self.reset + 'unknown argument "' + argument + '"')

    @property
    def red(self): return self.use_colors and self._color_RED or ''
    @property
    def green(self): return self.use_colors and self._color_GREEN or ''
    @property
    def brown(self): return self.use_colors and self._color_BROWN or ''
    @property
    def blue(self): return self.use_colors and self._color_BLUE or ''
    @property
    def magenta(self): return self.use_colors and self._color_MAGENTA or ''
    @property
    def cyan(self): return self.use_colors and self._color_CYAN or ''
    @property
    def white(self): return self.use_colors and self._color_WHITE or ''
    @property
    def red_bold(self): return self.use_colors and self._color_RED_BOLD or ''
    @property
    def blue_bold(self): return self.use_colors and self._color_BLUE_BOLD or ''
    @property
    def yellow(self): return self.use_colors and self._color_YELLOW or ''
    @property
    def reset(self): return self.use_colors and self.RESET or ''


mt_colors = MTcolors()
