#!/usr/bin/env python3

import os
import sys
import math
import time
import json
import queue
import datetime
import threading
import itertools as it
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

def get_ts ():
    return time.strftime(config.ts_format)

def get_rt (val):
    return time.strftime(config.rt_format, time.gmtime(val))

def aprint (*args, aqueue, **kwargs):
    aqueue.put(( ( "[{}]".format(get_ts()), *args ), kwargs ))

def beautify (data):
    colors = it.cycle(config.colors)

    return " ".join(
        "\033[38;5;{}m{}\033[0m".format(col, txt)
            for key, val in data
                for txt, col in zip(config.log_format(key, val), colors) if txt
    )

def begin (worker, *, log_queue):
    bold_id = "\033[1m{}\033[0m".format(worker.id)
    aprint(bold_id, "began", aqueue = log_queue)

def fetch (worker, ids, *, log_queue):
    bold_id = "\033[1m{}\033[0m".format(worker.id)
    aprint(bold_id, "recv", *ids, aqueue = log_queue)

def task (worker, data, pos, *, log_queue):
    bold_id = "\033[1m{}\033[0m".format(worker.id)
    ts_fmt = "[{}]".format
    beau = beautify(data)
    data = cl.OrderedDict(data)

    aprint(bold_id, "task", beau, aqueue = log_queue)

    start = time.time()
    config.run(worker.id, data, pos)
    runtime = "({})".format(get_rt(time.time() - start))

    aprint(bold_id, "done", beau, runtime, aqueue = log_queue)

def wait (worker, *, log_queue):
    bold_id = "\033[1m{}\033[0m".format(worker.id)
    ts_fmt = "[{}]".format

    aprint(bold_id, "wait {}s".format(config.wait_time), aqueue = log_queue)
    time.sleep(config.wait_time)

def end (worker, *, log_queue):
    bold_id = "\033[1m{}\033[0m".format(worker.id)
    ts_fmt = "[{}]".format
    aprint(bold_id, "end", aqueue = log_queue)

def main (argv):
    log_queue = queue.Queue()

    logger = threading.Thread(target = async_printer, kwargs = {
        "fname": config.log_fname, "aqueue": log_queue
    })

    logger.start()
    wrk = worker.worker(config.work_path)

    try:
        wrk.work(task, num_tasks = config.num_tasks,
                 begin = begin, fetch = fetch, wait = wait, end = end,
                 tkwargs = { "log_queue": log_queue },
                 bkwargs = { "log_queue": log_queue },
                 fkwargs = { "log_queue": log_queue },
                 wkwargs = { "log_queue": log_queue },
                 ekwargs = { "log_queue": log_queue })

    except KeyboardInterrupt:
        pass

    print("ending")

    log_queue.put(None)
    logger.join()

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
