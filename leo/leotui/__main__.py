"""
Run the terminal front end:  python -m leo.leotui FILE.leo [--dump]

The whole point of this program is what it does *not* import. It opens the
outline through leolib, attaches a leolib View, and edits the model directly.
Nothing here imports leoGlobals, leoCommands, leoBridge or any view module;
test_leotui_boundary asserts it.

--dump prints one composed frame and exits, so the view can be exercised in a
test or a pipe with no terminal at all.
"""

from __future__ import annotations
import argparse
import sys
from typing import Any

HELP = (
    ' j/k move  SPC fold  e head  i body  o ins  D del  KJ<> move  m mark '
    ' u/r undo  s save  W tangle  q quit '
)


def open_model(path: str, read_external: bool = True) -> Any:
    """Open a .leo file through leolib and give it one terminal view."""
    from leo import leolib
    from leo.leotui.model import OutlineModel

    outline = leolib.open_outline(path, read_external=read_external)
    model = OutlineModel(outline)
    model.select_current()
    return model


def prompt_line(stdscr: Any, row: int, prompt: str, initial: str = '') -> str | None:
    """A one-line editor. Returns None if the user pressed Escape."""
    import curses

    buf = list(initial)
    pos = len(buf)
    _, width = stdscr.getmaxyx()
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


def edit_body(stdscr: Any, model: Any) -> None:
    """
    A small full-screen body editor. Ctrl-S commits through the model, Escape
    abandons. Everything it types lands in the model, never in a widget the
    model then has to be told about.
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


def run_curses(model: Any) -> None:
    import curses

    from leo.leotui.screen import compose

    # Structural edits, straight to the model. There is no commander to run a
    # named command through; see leo/leotui/model.py.
    actions = {
        'o': model.insert_node,
        'D': model.delete_node,
        'K': model.move_up,
        'J': model.move_down,
        '<': model.move_left,
        '>': model.move_right,
        'm': model.toggle_mark,
    }

    def main(stdscr: Any) -> None:
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
            elif ch == 'u':
                message = '' if model.undo() else ' nothing to undo '
            elif ch == 'r':
                message = '' if model.redo() else ' nothing to redo '
            elif ch == 's':
                message = ' saved ' if model.save() else ' no file name: cannot save '
            elif ch == 'W':
                message = f" wrote {model.write_external_files()} external files "
            elif ch in actions:
                actions[ch]()
            elif ch == 'n':
                model.body_scroll += 1
            elif ch == 'p':
                model.body_scroll = max(0, model.body_scroll - 1)

    curses.wrapper(main)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m leo.leotui')
    parser.add_argument('path', help='a .leo file')
    parser.add_argument('--dump', action='store_true', help='print one frame and exit')
    parser.add_argument('--no-external', action='store_true', help='read the .leo file only')
    parser.add_argument('--width', type=int, default=100)
    parser.add_argument('--height', type=int, default=30)
    args = parser.parse_args(argv)

    model = open_model(args.path, read_external=not args.no_external)
    model.expand_all_ancestors()
    if args.dump:
        from leo.leotui.screen import compose

        for line in compose(model, args.width, args.height):
            print(line.rstrip())
        return 0
    run_curses(model)
    return 0


if __name__ == '__main__':
    sys.exit(main())
