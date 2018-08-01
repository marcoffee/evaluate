#!/usr/bin/env python3

import os
import sys
import mmap
import time
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

argparser = argparse.ArgumentParser()

argparser.add_argument("-o", dest = "output", default = config.pro_fname)
argparser.add_argument("-refresh", type = float, default = 1.0)

def main (argv):
    args = argparser.parse_args(argv)
    per_sec = 0.0

    done_file = os.path.join(config.work_path, config.don_fname)
    start_time = time.time()
    start_size = None
    mem_access = mmap.ACCESS_READ

    last_print = ""

    with open(done_file, "rb") as done, open(args.output, "w+") as out:
        with flock.flock(out, block = False):

            while True:
                count = None

                with mmap.mmap(done.fileno(), 0, access = mem_access) as mem:
                    count = sum(1 for _ in util.iter_done(mem))

                total = os.path.getsize(done_file) // config.one_size

                start_size = start_size or count
                delta = count - start_size

                percentage = 100 * count / total
                per_sec = delta / (time.time() - start_time)
                eta = sec_to_str((total - count) / per_sec) if per_sec else "-"

                next_print = "{} / {} = {:.2f}% ({:.2f} / s) ETA: {}".format(
                    count, total, percentage, per_sec, eta
                )

                print_diff = len(last_print) - len(next_print)

                if print_diff > 0:
                    next_print += " " * print_diff

                out.seek(0, os.SEEK_SET)
                print(next_print, file = out)
                alist.commit(out)

                last_print = next_print
                time.sleep(args.refresh)

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
