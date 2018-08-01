#!/usr/bin/env python3

import re
import sys
import time
import curses
import argparse
import datetime
import subprocess


argparser = argparse.ArgumentParser()
argparser.add_argument("command")
argparser.add_argument("-n", type = float, default = 1.0)
argparser.add_argument("-no-break", action = "store_false", dest = "brk")

def cprint (scr, py, px, y, x, dat, attr = curses.A_NORMAL, brk = False):
    if x < 0:
        dat = dat[ -x : ]
        x = 0

    if not dat:
        return py, px

    space = x - px

    if py >= (y - 1):
        return y, x

    line_break = b"\n" if isinstance(dat, bytes) else "\n"

    if dat.find(line_break) != -1:
        xpos = px
        ypos = py

        for line in dat.split(line_break):
            py, px = cprint(scr, ypos, xpos, y, x, line, attr, brk)
            ypos = py + 1
            xpos = 0

        return py, px

    if len(dat) > space:
        ypos, xpos = py, px

        if space > 0:
            this_line = dat[ : space ]
            ypos, xpos = cprint(scr, py, px, y, x, this_line, attr, brk)

        if brk:
            next_line = dat[ space : ]
            ypos, xpos = cprint(scr, py + 1, 0, y, x, next_line, attr, brk)

        return ypos, xpos

    scr.addstr(py, px, dat, attr)
    px = px + len(dat)

    return py, px

def main (argv):
    args = argparser.parse_args(argv)
    esc_reg = re.compile(b"(?:^|\033\[(.*?)m)([^\033]+)(?=\033|$)")

    try:
        scr = curses.initscr()
        curses.start_color()
        curses.use_default_colors()

        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        y, x = scr.getmaxyx()
        win = curses.newwin(y, x, 0, 0)

        while True:
            if curses.is_term_resized(y, x):
                y, x = scr.getmaxyx()
                curses.resizeterm(y, x)

            scr.clear()
            head_txt = "Every {}s: {}".format(args.n, args.command)
            cprint(scr, 0, 0, y, x, head_txt, brk = False)

            now = " [ {} ]".format(datetime.datetime.now())
            cprint(scr, 0, x - len(now), y, x, now, brk = False)

            res = subprocess.run(args.command, stdout = subprocess.PIPE,
                                 stderr = subprocess.STDOUT, shell = True)

            py = 2
            px = 0
            last_end = 0
            out = res.stdout

            ret = None

            for i, match in enumerate(esc_reg.finditer(out)):
                s, e = match.span()
                last_end = e
                attr = curses.A_NORMAL

                typ = match.group(1)

                if typ is not None:
                    typ = match.group(1).decode("ascii")

                    if typ == "1":
                        attr = curses.A_BOLD

                    elif typ.startswith("38;5;"):
                        attr = curses.color_pair(int(typ[ 5 : ]) + 1)

                    elif typ != "0":
                        raise Exception("Unknown escape command `{}`.".format(typ))

                s, e = match.span(2)
                txt = out[ s : e ]
                py, px = cprint(scr, py, px, y, x, txt, attr, args.brk)

            scr.refresh()
            time.sleep(args.n)

    except KeyboardInterrupt:
        pass

    finally:
        curses.endwin()
        curses.reset_shell_mode()

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
