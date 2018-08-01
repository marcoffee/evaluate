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

argparser = argparse.ArgumentParser()

argparser.add_argument("-o", dest = "output", default = config.pro_fname)
argparser.add_argument("-refresh", type = float, default = 1.0)
argparser.add_argument("-report", action = "store_true")

def main (argv):
    args = argparser.parse_args(argv)

    if args.report:
        with open(args.output, "rb") as file:
            data = file.read(config.use_bytes)
            count = int.from_bytes(data, config.use_order)

            data = file.read(config.use_bytes)
            total = int.from_bytes(data, config.use_order)

            data = file.read(config.use_bytes)
            start_size = int.from_bytes(data, config.use_order)

            data = file.read(struct.calcsize("<d"))
            start_time = struct.unpack("<d", data)[0]

            delta = count - start_size

            perc = 100 * count / total
            per_sec = delta / (time.time() - start_time)
            eta = sec_to_str((total - count) / per_sec) if per_sec else "-"

            print("{} / {} = {:.2f}%".format(count, total, perc), end = " ")

            if count != total:
                print("({:.2f} / s) ETA: {}".format(per_sec, eta))
            else:
                print("\033[1mdone\033[0m")

            return

    done_file = os.path.join(config.work_path, config.don_fname)
    start_time = time.time()
    mem_access = mmap.ACCESS_READ
    start_size = 0
    first_work = 0

    with open(done_file, "rb") as done, open(args.output, "wb+") as out:
        with flock.flock(out, block = False):

            while True:
                count = first_work // config.one_size
                fsize = os.path.getsize(done_file)
                total = fsize // config.one_size

                with mmap.mmap(done.fileno(), 0, access = mem_access) as mem:
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

                out.seek(0, os.SEEK_SET)
                out.write(count.to_bytes(config.use_bytes, config.use_order))
                out.write(total.to_bytes(config.use_bytes, config.use_order))
                out.write(start_size.to_bytes(config.use_bytes, config.use_order))
                out.write(struct.pack("<d", start_time))
                alist.commit(out)

                if count == total:
                    break

                time.sleep(args.refresh)

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
