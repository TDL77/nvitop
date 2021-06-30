# This file is part of nvitop, the interactive NVIDIA-GPU process viewer.
# License: GNU GPL version 3.

# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=invalid-name

from collections import OrderedDict
from functools import partial

from ...core import host, HostProcess, GpuProcess
from ..library import Displayable


class EnvironScreen(Displayable):
    def __init__(self, win, root):
        super().__init__(win, root)

        self.this = HostProcess()

        self.previous_screen = 'main'

        self._process = None
        self._environ = None

        self.x_offset = 0
        self._y_offset = 0
        self.scroll_offset = 0

        self._height = 0
        self.width, self.height = root.width, root.height

    @property
    def process(self):
        return self._process

    @process.setter
    def process(self, value):
        if value is None:
            value = self.this

        self._process = value
        try:
            self.environ = self.process.environ().copy()
        except host.PsutilError:
            self.environ = None

    @property
    def environ(self):
        return self._environ

    @environ.setter
    def environ(self, value):
        if value is not None:
            value = OrderedDict([(key, value[key]) for key in sorted(value.keys())])
        self._environ = value
        self.y_offset = 0
        self.scroll_offset = 0

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value
        try:
            self.y_offset = self.y_offset
        except AttributeError:
            pass

    @property
    def y_offset(self):
        return self._y_offset

    @y_offset.setter
    def y_offset(self, value):
        if self.environ is None:
            self._y_offset = 0
            self.scroll_offset = 0
            return

        n_items = len(self.environ)
        self._y_offset = max(0, min(value, n_items - 1))
        if self.y + 2 + n_items <= self.scroll_offset + self.height:
            self.scroll_offset = max(0, self.y + 2 + n_items - self.height)
        elif self.y + 2 + self.y_offset > self.scroll_offset + self.height - 1:
            self.scroll_offset = self.y + 2 + self.y_offset - self.height + 1
        self.scroll_offset = min(self.scroll_offset, self.y_offset)

    def move(self, direction):
        self.y_offset = self.y_offset + direction

    def draw(self):
        self.color_reset()

        try:
            name = self.process.name()
        except host.PsutilError:
            name = 'N/A'

        if isinstance(self.process, GpuProcess):
            process_type = 'GPU: {}'.format(self.process.type.replace('C', 'Compute').replace('G', 'Graphics'))
        else:
            process_type = 'Host'
        header = 'Environment of process {} ({}) - {}'.format(self.process.pid, process_type, name)

        self.addstr(self.y, self.x, header.ljust(self.width))
        self.addstr(self.y + 1, self.x, '#' * self.width)
        self.color_at(self.y, self.x, width=self.width, fg='cyan', attr='bold')
        self.color_at(self.y + 1, self.x, width=self.width, fg='green', attr='bold')

        if self.environ is None:
            self.addstr(self.y + 2, self.x, 'Could not read process environment.')
            self.color_at(self.y + 2, self.x, width=self.width, fg='cyan', attr='reverse')
            return

        for y, (key, value) in enumerate(self.environ.items(), start=self.y + 2 - self.scroll_offset):
            if not 2 <= y - self.y < self.height:
                continue

            key_length = len(key)
            line = '{}={}'.format(key, value)
            self.addstr(y, self.x, line[self.x_offset:self.x_offset + self.width].ljust(self.width))
            if self.x_offset < key_length:
                self.color_at(y, self.x, width=key_length - self.x_offset, fg='blue', attr='bold')
            if self.x_offset < key_length + 1:
                self.color_at(y, self.x + key_length - self.x_offset, width=1, fg='magenta')

            if y == self.y + 2 - self.scroll_offset + self.y_offset:
                self.color_at(y, self.x, width=self.width, fg='cyan', attr='bold | reverse')

    def press(self, key):
        self.root.keymaps.use_keymap('environ')
        self.root.press(key)

    def click(self, event):
        direction = event.wheel_direction()
        if event.shift():
            self.x_offset = max(0, self.x_offset + 2 * direction)
        else:
            self.move(direction=direction)
        return True

    def init_keybindings(self):
        # pylint: disable=multiple-statements

        def refresh_environ(top):
            top.main_screen.visible = False
            top.treeview_screen.visible = False
            top.help_screen.visible = False

            top.environ_screen.visible = True
            top.environ_screen.focused = True

            if top.environ_screen.previous_screen == 'treeview':
                top.environ_screen.process = top.treeview_screen.selected.process
            else:
                top.environ_screen.process = top.main_screen.selected.process

        def environ_left(top): top.environ_screen.x_offset = max(0, top.environ_screen.x_offset - 5)
        def environ_right(top): top.environ_screen.x_offset += 5
        def environ_begin(top): top.environ_screen.x_offset = 0
        def environ_move(top, direction): top.environ_screen.move(direction=direction)

        self.root.keymaps.bind('environ', 'r', refresh_environ)
        self.root.keymaps.copy('environ', 'r', 'R')
        self.root.keymaps.copy('environ', 'r', '<C-r>')
        self.root.keymaps.copy('environ', 'r', '<F5>')
        self.root.keymaps.bind('environ', '<Left>', environ_left)
        self.root.keymaps.copy('environ', '<Left>', '[')
        self.root.keymaps.copy('environ', '<Left>', '<A-h>')
        self.root.keymaps.bind('environ', '<Right>', environ_right)
        self.root.keymaps.copy('environ', '<Right>', ']')
        self.root.keymaps.copy('environ', '<Right>', '<A-l>')
        self.root.keymaps.bind('environ', '<C-a>', environ_begin)
        self.root.keymaps.copy('environ', '<C-a>', '^')
        self.root.keymaps.bind('environ', '<Up>', partial(environ_move, direction=-1))
        self.root.keymaps.copy('environ', '<Up>', '<S-Tab>')
        self.root.keymaps.copy('environ', '<Up>', '<A-k>')
        self.root.keymaps.bind('environ', '<Down>', partial(environ_move, direction=+1))
        self.root.keymaps.copy('environ', '<Down>', '<Tab>')
        self.root.keymaps.copy('environ', '<Down>', '<A-j>')
        self.root.keymaps.bind('environ', '<Home>', partial(environ_move, direction=-(1 << 20)))
        self.root.keymaps.bind('environ', '<End>', partial(environ_move, direction=+(1 << 20)))
