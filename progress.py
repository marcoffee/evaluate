#!/usr/bin/env python3

import os
import sys
import mmap
import time
import struct
import argparse

import util
import alist
import flock
import config


def sec_to_str (sec):
    days, sec = divmod(sec, 86400)
    hours, sec = divmod(sec, 3600)
    minutes, sec = divmod(sec, 60)

    result = "{:>08.5f}".format(sec)

    if minutes or hours or days:
        result = "{:>02.0f}:{}".format(minutes, result)

        if hours or days:
            result = "{:>02.0f}:{}".format(hours, result)

            if days:
                result = "{:.0f}-{}".format(days, result)

    return result

argparser = argparse.ArgumentParser(prog = os.path.basename(__file__))

argparser.add_argument("-refresh", type = float, default = 1.0)
argparser.add_argument("-report", action = "store_true")
argparser.add_argument("-no-print", action = "store_false", dest = "print")

def main (argv):
    args = argparser.parse_args(argv)

    if args.report:
        out = ""

        with open(config.files.progress, "rb") as file:
            data = file.read(struct.calcsize(config.pro_format))
            data = struct.unpack(config.pro_format, data)
            count, total, start_size, start_time = data

            delta = count - start_size

            perc = 100 * count / total
            per_sec = delta / (time.time() - start_time)
            eta = sec_to_str((total - count) / per_sec) if per_sec else "-"

            out = "{} / {} = {:.2f}% ".format(count, total, perc)

            if count != total:
                out += "({:.2f} / s) ETA: {}".format(per_sec, eta)
            else:
                out += "\033[1mdone\033[0m"

            if args.print:
                print(out)

        return out

    start_time = time.time()
    mem_access = mmap.ACCESS_READ
    start_size = 0
    first_work = 0

    with open(config.files.done, "rb") as done, \
         open(config.files.progress, "wb+") as prog:

        with flock.flock(prog, block = False):
            try:
                while True:
                    count = first_work // config.one_size
                    fsize = os.path.getsize(config.files.done)
                    total = fsize // config.one_size
                    done_fn = done.fileno()

                    with mmap.mmap(done_fn, 0, access = mem_access) as mem:
                        prev = first_work
                        found_work = False

                        for s, e in util.iter_done(mem, start = first_work):
                            count += 1

                            if not found_work:
                                found_work = prev != s

                                if not found_work:
                                    prev = e

                        first_work = prev

                    start_size = start_size or count

                    prog.seek(0, os.SEEK_SET)
                    prog.write(struct.pack(
                        config.pro_format, count, total, start_size, start_time
                    ))
                    alist.commit(prog)

                    if count == total:
                        break

                    time.sleep(args.refresh)

            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
