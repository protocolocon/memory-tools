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

def save_thread_frame():
    return gdb.selected_thread(), gdb.selected_frame()

def restore_thread_frame(thread, frame):
    thread.switch()
    frame.select()

def get_frame_number(thread, frame): # thread has to be selected
    'Compute frame number and leave original status'
    frame.select()
    frame_num = -1
    f = frame
    while f and f.is_valid():
        f = f.newer()
        frame_num += 1
    return frame_num

def get_value(symbol, frame): # thread has to be selected
    'Get value from symbol'
    if symbol.addr_class not in { gdb.SYMBOL_LOC_TYPEDEF, gdb.SYMBOL_LOC_UNRESOLVED, gdb.SYMBOL_LOC_LABEL }:
        value = symbol.value(frame)
        return value
    return None

def maintain_thread_frame(func):
    'Decorator to maintain thread and frame status'
    def wrap(self, *args, **kwargs):
        prev_thread, prev_frame = save_thread_frame()
        ret = func(self, *args, **kwargs)
        restore_thread_frame(prev_thread, prev_frame)
        return ret
    return wrap
