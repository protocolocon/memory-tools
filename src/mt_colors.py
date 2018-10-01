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

RED       = '\033[31m'
GREEN     = '\033[32m'
BROWN     = '\033[33m'
BLUE      = '\033[34m'
MAGENTA   = '\033[35m'
CYAN      = '\033[36m'
WHITE     = '\033[37m'
RED_BOLD  = '\033[1;31m'
BLUE_BOLD = '\033[1;34m'
YELLOW    = '\033[1;33m'
RESET     = '\033[0m'

# optionally use colors
class MTcolors:
    def __init__(self):
        self.use_colors = True

    def use(self, argument, from_tty):
        if not argument:
            self.use_colors = not self.use_colors
            if from_tty: print(self.cyan + 'colors: ' + self.green + (self.use_colors and 'ON' or 'OFF') + self.reset)
        elif argument.lower() == 'on':
            self.use_colors = True
        elif argument.lower() == 'off':
            self.use_colors = False
        else:
            print(self.red + 'error: ' + self.reset + 'unknown argument "' + argument + '"')

    @property
    def red(self): return self.use_colors and RED or ''
    @property
    def green(self): return self.use_colors and GREEN or ''
    @property
    def brown(self): return self.use_colors and BROWN or ''
    @property
    def blue(self): return self.use_colors and BLUE or ''
    @property
    def magenta(self): return self.use_colors and MAGENTA or ''
    @property
    def cyan(self): return self.use_colors and CYAN or ''
    @property
    def white(self): return self.use_colors and WHITE or ''
    @property
    def red_bold(self): return self.use_colors and RED_BOLD or ''
    @property
    def blue_bold(self): return self.use_colors and BLUE_BOLD or ''
    @property
    def yellow(self): return self.use_colors and YELLOW or ''
    @property
    def reset(self): return self.use_colors and RESET or ''


mt_colors = MTcolors()
