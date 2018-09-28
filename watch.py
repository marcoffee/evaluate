#!/usr/bin/env python3

import re
import sys
import time
import curses
import argparse
import datetime
import traceback
import subprocess


def run_forever ():
    return False

def cprint (scr, py, px, y, x, dat, attr = curses.A_NORMAL, brk = False):
    if x < 0:
        dat = dat[ -x : ]
        x = 0

    if not dat:
        return py, px

    space = x - px

    if py >= (y - 1):
        return y, x

    if dat.find("\n") != -1:
        xpos = px
        ypos = py

        for line in dat.split("\n"):
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

esc_reg = re.compile(r"(?:^|\033\[(.*?)m)([^\033]+)(?=\033|$)")

def window (scr, func, refresh, time_fmt, brk, run_until, command):
    curses.use_default_colors()

    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)

    y, x = scr.getmaxyx()
    win = curses.newwin(y, x, 0, 0)

    while not run_until():

        if curses.is_term_resized(y, x):
            y, x = scr.getmaxyx()
            curses.resizeterm(y, x)

        scr.clear()
        head_txt = "Every {}s".format(refresh)

        if command:
            head_txt += ": {}".format(command)

        cprint(scr, 0, 0, y, x, head_txt, brk = False)

        now = datetime.datetime.now()
        ts = " [ {} ]".format(now.strftime(time_fmt))
        cprint(scr, 0, x - len(ts), y, x, ts, brk = False)

        try:
            out = func()
        except:
            out = traceback.format_exc()

        py = 2
        px = 0
        last_end = 0

        ret = None

        for i, match in enumerate(esc_reg.finditer(out)):
            s, e = match.span()
            last_end = e
            attr = curses.A_NORMAL

            typ = match.group(1)

            if typ is not None:
                typ = match.group(1)

                if typ == "1":
                    attr = curses.A_BOLD

                elif typ.startswith("38;5;"):
                    attr = curses.color_pair(int(typ[ 5 : ]) + 1)

                elif typ != "0":
                    raise Exception("Unknown escape command `{}`.".format(typ))

            s, e = match.span(2)
            txt = out[ s : e ]
            py, px = cprint(scr, py, px, y, x, txt, attr, brk)

        curses.curs_set(0)
        scr.refresh()
        time.sleep(refresh)

def watch (
    func, refresh = 1, time_fmt = "%Y-%m-%d %H:%M:%S.%f",
    brk = True, run_until = run_forever, command = ""
):
    curses.wrapper(window, func, refresh, time_fmt, brk, run_until, command)

def main (argv):
    argparser = argparse.ArgumentParser()
    argparser.add_argument("command")
    argparser.add_argument("-n", type = float, default = 1.0)
    argparser.add_argument("-no-break", action = "store_false", dest = "brk")
    argparser.add_argument("-time-format", default = "%Y-%m-%d %H:%M:%S.%f")

    args = argparser.parse_args(argv)

    try:
        func = lambda: subprocess.run(
            args.command, stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT, shell = True,
            universal_newlines = True
        ).stdout

        watch(func, args.n, args.time_format, args.brk, command = args.command)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
