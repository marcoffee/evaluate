#!/usr/bin/env python3

import os
import time
import math
import argparse
import itertools as it
import collections as cl
import subprocess as sp
import testconfig
import adeque
import worker


max_dset = max(map(len, map(testconfig.get_name, testconfig.benchmarks)))
max_seed = math.floor(math.log10(testconfig.seed_stop)) + 1

def work (worker, tid, data, short = False, quiet = True):
    time_point = time.time()

    bench, seed, flags = data
    dset = testconfig.get_name(bench)
    expe = cl.deque(testconfig.sanitize_exp(flags))

    dat_path = "{}/{}".format(testconfig.rst_path, dset)

    tst_name = testconfig.get_fname(expe)

    tst_path = os.path.join(dat_path, tst_name)
    sed_path = "{}/{}".format(tst_path, seed)

    if not quiet:
        print(worker.id, "got", "{}@{}".format(dset, seed), end = " => ")
        print(*map(": ".join, expe), sep = ", ")

    flags = { **flags, **testconfig.fixed }

    # positional arguments and benchmark related flags
    argv = []

    if not short:
        # benchmark related flags that may create large files
        argv.extend([])

    for f, v in flags.items():
        if v is testconfig.REMOVE:
            continue

        argv.append(str(f))

        if v is testconfig.ENABLE:
            continue

        if not isinstance(v, str) and isinstance(v, cl.Iterable):
            argv.extend(map(str, v))

        else:
            argv.append(str(v))

    os.makedirs(sed_path, exist_ok = True)

    # execute your script with argv here

    max_id = worker.id

    try:
        with open(worker.id_file, "r") as file:
            max_id = max(0, int(file.readline().strip() or 1) - 1)

    except FileNotFoundError:
        pass

    max_work = math.floor(math.log10(max_id)) + 1

    expe.appendleft(( "seed", "{: >{}d}".format(seed, max_seed) ))
    expe.appendleft(( "dset", dset.rjust(max_dset) ))
    expe.appendleft(( "work", "{: >{}d}".format(worker.id, max_work) ))

    expe.append(( "end", time.strftime("%Y%m%d.%H%M%S", time.gmtime()) ))
    expe.append(( "time", "{:.5f}s".format(time.time() - time_point) ))

    with adeque.LockFile(testconfig.tst_file, "a") as file:
        file.seek(0, os.SEEK_END)
        print(*map(": ".join, expe), sep = ", ", file = file, flush = True)

argparser = argparse.ArgumentParser()
argparser.add_argument("-no-quiet", action = "store_false", dest = "quiet")
argparser.add_argument("-short", action = "store_true")

if __name__ == '__main__':
    args = argparser.parse_args()

    if not args.quiet:
        testconfig.disable_quiet()

    worker.Worker(testconfig.deq_name, testconfig.deq_path).work(
        work, max_tasks = testconfig.max_tasks, fkwargs = {
            "quiet": args.quiet, "short": args.short
        }
    )
