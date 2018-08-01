#!/usr/bin/env python3

import os
import sys
import math
import time
import json
import queue
import threading
import collections as cl

import flock
import alist
import config
import worker


def get_many (aqueue, block_first = False):
    if block_first:
        yield aqueue.get()

    while True:
        try:
            value = aqueue.get(False)
            yield value
        except queue.Empty:
            break

def async_printer (fname, aqueue):
    if fname == os.devnull:
        return

    alist.mkfile(fname)

    with open(fname, "r+") as log:
        stop = False

        while not stop:
            buffer = []

            for data in get_many(aqueue, True):
                stop = data is None

                if stop:
                    break

                buffer.append(data)

            if buffer:
                with flock.flock(log):
                    log.seek(0, os.SEEK_END)

                    for args, kwargs in buffer:
                        print(*args, **kwargs, file = log)

                    alist.commit(log)

def aprint (*args, aqueue, **kwargs):
    aqueue.put(( args, kwargs ))

def value_name (val):
    if val is config.ENABLE:
        return "<enable>"

    elif val is config.DISABLE:
        return "<disable>"

    return str(val)

def beautify (data):
    fmt = "\033[38;5;{}m{} = {}\033[0m".format

    return " ".join(
        fmt(config.colors[i % len(config.colors)], k, value_name(v))
            for i, ( k, v ) in enumerate(data)
    )

def work (worker, data, pos, *, log_queue):
    beautified = beautify(data)
    data = cl.OrderedDict(data)

    bold_id = "\033[1m{}\033[0m".format(worker.id)

    aprint(bold_id, "got", beautified, aqueue = log_queue)
    config.run(data)
    aprint(bold_id, "done", beautified, aqueue = log_queue)

def wait (worker, *, log_queue):
    aprint(worker.id, "is waiting", config.wait_time, "s", aqueue = log_queue)
    time.sleep(config.wait_time)

def main (argv):
    log_queue = queue.Queue()

    logger = threading.Thread(target = async_printer, kwargs = {
        "fname": config.log_fname, "aqueue": log_queue
    })

    logger.start()
    wrk = worker.worker(config.work_path)

    try:
        wrk.work(work, num_tasks = config.num_tasks, wait = wait,
                 fkwargs = { "log_queue": log_queue },
                 wkwargs = { "log_queue": log_queue })

    except KeyboardInterrupt:
        pass

    print("ending")

    log_queue.put(None)
    logger.join()

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
