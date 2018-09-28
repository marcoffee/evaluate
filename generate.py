#!/usr/bin/env python3

import os
import sys
import struct
import argparse
import itertools as it
import collections as cl

import flock
import alist
import config


def iter_keys (defaults, tests):
    unique = set()

    for key in defaults.keys():
        yield key
        unique.add(key)

    for test in tests:
        for key, _ in test:
            if key not in unique:
                yield key
                unique.add(key)

def iter_values (defaults, tests):
    unique = {}

    for key, val in defaults.items():
        unique[key] = { val }
        yield key, val

    for test in tests:
        for key, vals in test:
            for val in vals:
                if val not in unique[key]:
                    yield key, val

def iter_tests (defaults, tests, order):
    key = lambda x: order[x[0]]

    for test in tests:
        keys = [ key for key, _ in test ]
        opts = [ opt for _, opt in test ]

        for vals in it.product(*opts):
            flags = { **defaults, **dict(zip(keys, vals)) }
            flags = cl.OrderedDict(sorted(flags.items(), key = key))

            if config.ignore(flags):
                continue

            yield tuple(flags.items())

argparser = argparse.ArgumentParser(prog = os.path.basename(__file__))
argparser.add_argument("-clear", action = "store_true")
argparser.add_argument("-release-tasks", action = "store_true")
argparser.add_argument("-no-warnings", action = "store_false", dest = "warnings")

def main (argv):
    args = argparser.parse_args(argv)

    defaults = cl.OrderedDict(config.defaults)
    order = { param : i for i, param in enumerate(defaults.keys()) }

    for key in iter_keys(defaults, config.tests):
        if key in defaults:
            continue

        pos = len(order)
        defaults[key] = DISABLE
        order[key] = pos

        if args.warnings:
            warn = "Using DISABLE as default and `{}` as order for `{}`."
            print(warn.format(pos, key))

    for key, val in iter_values(defaults, config.tests):
        config.preprocess(key, val)

    os.makedirs(config.paths.task, exist_ok = True)
    os.makedirs(config.paths.lock, exist_ok = True)

    alist.mkfile(config.files.wid, config.files.done,
                 config.files.data, config.files.log, config.files.progress)

    with open(config.files.progress, "rb+") as file:
        try:
            with flock.flock(file, block = False):
                file.seek(0, os.SEEK_SET)
                zeros = b"\x00" * struct.calcsize(config.pro_format)
                file.write(zeros)

        except flock.LockedException:
            pass

    o_type = "wb+" if args.clear else "rb+"

    with open(config.files.data, o_type) as queue, \
         open(config.files.done, o_type) as done:

        with flock.flock(queue), flock.flock(done):
            exists = set()

            for task in alist.iterate_locked(queue):
                exists.add(tuple(sorted(task)))

            created = alist.write_locked(queue, *(
                ts for ts in iter_tests(defaults, config.tests, order)
                    if tuple(sorted(ts)) not in exists
            ))

            for _ in range(created):
                done.seek(0, os.SEEK_END)
                done.write(config.sep_free)

            if not args.clear and args.release_tasks:
                done.seek(0, os.SEEK_SET)

                with mmap.mmap(done.fileno(), 0) as mem:
                    for s, e in util.iter_work(mem):
                        mem[ s : e ] = config.sep_free

            print("created", created, "experiments")

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
