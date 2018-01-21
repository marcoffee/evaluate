#!/usr/bin/env python3

import os
import sys
import subprocess
import testconfig
import adeque
import argparse


argparser = argparse.ArgumentParser()
argparser.add_argument("-no-clear", action = "store_false", dest = "clear")
args = argparser.parse_args()

for _, params, _ in testconfig.tests:
    for p in params:
        if p not in testconfig.default:
            raise Exception("{} should have a default value.".format(p))

tested = {}

try:
    with open(testconfig.tst_file) as file:
        for line in file:
            flags = {}

            for line in line.strip().split(",")[ 1 : -2 ]:
                kv = line.split(":")

                if len(kv) > 1:
                    flags[kv[0].strip()] = kv[1].strip()
                else:
                    flags[line.strip()] = testconfig.ENABLE

            seed = int(flags.pop("seed"))
            dset = flags.pop("dset")
            expe = tuple(testconfig.sanitize_exp(flags))

            tested.setdefault(dset, {}).setdefault(expe, set()).add(seed)

except FileNotFoundError:
    pass

experiments = []

with adeque.Deque(testconfig.deq_name, testconfig.deq_path) as deque:

    if args.clear:
        deque.clear()
    else:
        for wid, tid, ( bench, seed, flags ) in deque:
            dset = testconfig.get_name(bench)
            expe = tuple(testconfig.sanitize_exp(flags))
            tested.setdefault(dset, {}).setdefault(expe, set()).add(seed)

    for benchmark, tests in testconfig.iter_tests():
        dset = testconfig.get_name(benchmark)
        print(dset)

        # add code here if you need to treat your benchmark before running

        for flags in tests:

            expe = tuple(testconfig.sanitize_exp(flags))
            exptest = tested.get(dset, {}).get(expe, set())

            print(expe)

            experiments.extend((
                ( None, ( benchmark, seed, flags ) )
                    for seed in range(testconfig.seed_start, testconfig.seed_stop)
                        if seed not in exptest
            ))

        print()

    print("created", len(experiments), "experiments")
    deque.push(*experiments)

count_tested = sum(len(seeds) for dsets in tested.values()
                   for seeds in dsets.values())

with open(testconfig.siz_file, "w") as file:
    print(len(experiments) + count_tested, file = file)
