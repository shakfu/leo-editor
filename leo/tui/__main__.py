# @+leo-ver=5-thin
# @+node:sa.20260905210300.1: * @file ../tui/__main__.py
"""
Run the terminal view:  python -m leo.tui FILE.leo [--dump]

--dump prints one composed frame and exits, so the view can be exercised in a
test or a pipe with no terminal at all.
"""

# @+<< tui.__main__ imports >>
# @+node:sa.20260905210300.2: ** << tui.__main__ imports >>
from __future__ import annotations
import argparse
import os
import sys
# @-<< tui.__main__ imports >>


# @+others
# @+node:sa.20260905210300.3: ** function: open_outline
def open_outline(path: str):
    """Open a .leo file with no gui at all and return its commander."""
    from leo.core import leoBridge

    bridge = leoBridge.controller(
        gui='nullGui', loadPlugins=False, readSettings=False, silent=True, verbose=False
    )
    return bridge.openLeoFile(os.path.abspath(os.path.expanduser(path)))


# @+node:sa.20260905220100.1: ** function: prompt_line
def prompt_line(stdscr: object, row: int, prompt: str, initial: str = '') -> str | None:
    """A one-line editor. Returns None if the user pressed Escape."""
    import curses

    buf = list(initial)
    pos = len(buf)
    height, width = stdscr.getmaxyx()
    while True:
        text = ''.join(buf)
        line = (prompt + text)[: width - 1]
        stdscr.move(row, 0)
        stdscr.clrtoeol()
        stdscr.addstr(row, 0, line)
        stdscr.move(row, min(len(prompt) + pos, width - 1))
        curses.curs_set(1)
        k = stdscr.getch()
        if k == 27:  # Escape
            curses.curs_set(0)
            return None
        if k in (10, 13):
            curses.curs_set(0)
            return ''.join(buf)
        if k in (curses.KEY_BACKSPACE, 127, 8):
            if pos:
                del buf[pos - 1]
                pos -= 1
        elif k == curses.KEY_DC:
            if pos < len(buf):
                del buf[pos]
        elif k == curses.KEY_LEFT:
            pos = max(0, pos - 1)
        elif k == curses.KEY_RIGHT:
            pos = min(len(buf), pos + 1)
        elif k == curses.KEY_HOME:
            pos = 0
        elif k == curses.KEY_END:
            pos = len(buf)
        elif 32 <= k < 127:
            buf.insert(pos, chr(k))
            pos += 1


# @+node:sa.20260905220200.1: ** function: edit_body
def edit_body(stdscr: object, model: object) -> None:
    """
    A small full-screen body editor. Ctrl-S commits through the model, Escape
    abandons. Everything it types lands in p.b via the undoer, never in a
    widget that the model then has to be told about.
    """
    import curses

    lines = model.body_lines() or ['']
    row, col = 0, 0
    while True:
        height, width = stdscr.getmaxyx()
        stdscr.erase()
        top = max(0, row - (height - 3) // 2)
        for i in range(height - 2):
            n = top + i
            if n < len(lines):
                stdscr.addstr(i, 0, lines[n][: width - 1])
        status = f" edit: {model.current.h}   ^S save   ESC cancel   {row + 1}:{col + 1} "
        stdscr.addstr(height - 1, 0, status[: width - 1], curses.A_REVERSE)
        stdscr.move(min(row - top, height - 3), min(col, width - 1))
        curses.curs_set(1)
        k = stdscr.getch()
        if k == 27:
            curses.curs_set(0)
            return
        if k == 19:  # Ctrl-S
            curses.curs_set(0)
            insert = sum(len(z) + 1 for z in lines[:row]) + col
            model.set_body('\n'.join(lines), insert)
            return
        if k in (10, 13):
            rest = lines[row][col:]
            lines[row] = lines[row][:col]
            lines.insert(row + 1, rest)
            row, col = row + 1, 0
        elif k in (curses.KEY_BACKSPACE, 127, 8):
            if col:
                lines[row] = lines[row][: col - 1] + lines[row][col:]
                col -= 1
            elif row:
                col = len(lines[row - 1])
                lines[row - 1] += lines.pop(row)
                row -= 1
        elif k == curses.KEY_UP:
            row = max(0, row - 1)
            col = min(col, len(lines[row]))
        elif k == curses.KEY_DOWN:
            row = min(len(lines) - 1, row + 1)
            col = min(col, len(lines[row]))
        elif k == curses.KEY_LEFT:
            col = max(0, col - 1)
        elif k == curses.KEY_RIGHT:
            col = min(len(lines[row]), col + 1)
        elif k == curses.KEY_HOME:
            col = 0
        elif k == curses.KEY_END:
            col = len(lines[row])
        elif 32 <= k < 127 or k == 9:
            ch = '    ' if k == 9 else chr(k)
            lines[row] = lines[row][:col] + ch + lines[row][col:]
            col += len(ch)


# @+node:sa.20260905210300.4: ** function: run_curses
# Keys that dispatch straight to one of Leo's own commands. All of these were
# verified to work with a null frame, so the terminal view drives the real
# outline machinery rather than reimplementing it.
COMMAND_KEYS = {
    'o': 'insert-node',
    'D': 'delete-node',
    'u': 'undo',
    'r': 'redo',
    'K': 'move-outline-up',
    'J': 'move-outline-down',
    '<': 'move-outline-left',
    '>': 'move-outline-right',
    'm': 'toggle-mark',
    'c': 'clone-node',
    'y': 'copy-node',
    'P': 'paste-node',
}

HELP = ' j/k move  SPC fold  e head  i body  o ins  D del  u/r undo  KJ<> move  m mark  s save  q quit '


def run_curses(model) -> None:
    import curses

    from leo.tui.screen import compose

    def main(stdscr: object) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        message = ''
        while True:
            height, width = stdscr.getmaxyx()
            lines = compose(model, width - 1, height - 2)
            stdscr.erase()
            for i, line in enumerate(lines):
                try:
                    stdscr.addstr(i, 0, line)
                except curses.error:
                    pass
            try:
                stdscr.addstr(height - 1, 0, (message or HELP)[: width - 1], curses.A_REVERSE)
            except curses.error:
                pass
            stdscr.refresh()
            message = ''
            k = stdscr.getch()
            ch = chr(k) if 0 <= k < 256 else ''
            if ch == 'q':
                return
            if k in (curses.KEY_DOWN, ord('j')):
                model.move(1)
            elif k in (curses.KEY_UP, ord('k')):
                model.move(-1)
            elif k == curses.KEY_NPAGE:
                model.move(10)
            elif k == curses.KEY_PPAGE:
                model.move(-10)
            elif k in (ord(' '), curses.KEY_RIGHT, curses.KEY_LEFT, 10, 13):
                model.toggle()
            elif ch == 'e':
                new = prompt_line(stdscr, height - 1, 'headline: ', model.current.h)
                if new is not None:
                    model.set_headline(new)
            elif ch == 'i':
                edit_body(stdscr, model)
            elif ch == 's':
                message = ' saved ' if model.save() else ' no file name: cannot save '
            elif ch in COMMAND_KEYS:
                model.run_command(COMMAND_KEYS[ch])
            elif ch == 'n':
                model.body_scroll += 1
            elif ch == 'p':
                model.body_scroll = max(0, model.body_scroll - 1)

    curses.wrapper(main)


# @+node:sa.20260905210300.5: ** function: main
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m leo.tui')
    parser.add_argument('path', help='a .leo file')
    parser.add_argument('--dump', action='store_true', help='print one frame and exit')
    parser.add_argument('--width', type=int, default=100)
    parser.add_argument('--height', type=int, default=30)
    args = parser.parse_args(argv)

    sys.argv = [sys.argv[0]]  # leoBridge parses sys.argv.
    c = open_outline(args.path)

    from leo.tui.model import OutlineModel

    model = OutlineModel(c)
    model.expand_all_ancestors()
    if args.dump:
        from leo.tui.screen import compose

        for line in compose(model, args.width, args.height):
            print(line.rstrip())
        return 0
    run_curses(model)
    return 0


# @-others
if __name__ == '__main__':
    sys.exit(main())
# @@language python
# @@tabwidth -4
# @-leo
