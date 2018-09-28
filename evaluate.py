#!/usr/bin/env python3

import os
import sys
import math
import time
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
    return datetime.datetime.now().strftime(config.ts_format)

def get_rt (val):
    return datetime.datetime.utcfromtimestamp(val).strftime(config.rt_format)

def aprint (*args, aqueue, ts = True, **kwargs):
    if ts:
        args = ( "[{}]".format(get_ts()), *args )

    aqueue.put(( args, kwargs ))

def beautify (data):
    colors = it.cycle(config.colors)

    return " ".join(
        "\033[38;5;{}m{}\033[0m".format(col, txt)
            for key, val in data
                for txt, col in zip(config.log_format(key, val), colors) if txt
    )

def bold (txt):
    return "\033[1m{}\033[0m".format(txt)

def color_reason (tid, rea):
    fmt = "{}"

    if rea == "free":
        fmt = "\033[38;5;{}m{{}}\033[0m".format(config.recv_free)

    elif rea == "mine":
        fmt = "\033[38;5;{}m{{}}\033[0m".format(config.recv_mine)

    elif rea == "dead":
        fmt = "\033[38;5;{}m{{}}\033[0m".format(config.recv_dead)

    return fmt.format(tid)

def format_reason (tid, rea, wid):
    result = color_reason(tid, rea)

    if rea == "dead":
        result = "{} <- {}".format(bold(wid), result)

    return result

def begin (worker, *, aqueue):
    aprint(bold(worker.id), "began", aqueue = aqueue)

def starve (worker, amount, *, aqueue):
    aprint(bold(worker.id), "is starving", "#{}".format(amount), aqueue = aqueue)

def fetch (worker, ids, reason, *, aqueue):
    printed = []

    aprint(bold(worker.id), "recv", aqueue = aqueue, end = " ")

    for tid, ( rea, rid ) in zip(ids, reason):
        printed.append(format_reason(tid, rea, rid))

        if len(printed) >= config.max_recv:
            break

    aprint(*printed, ts = False, sep = ", ", aqueue = aqueue, end = " ")

    if len(ids) > len(printed):
        diff = "... +{}".format(len(ids) - len(printed))
        aprint(diff, "tasks", ts = False, aqueue = aqueue, end = "")

    aprint(ts = False, aqueue = aqueue)

def task (worker, data, pos, rea, *, aqueue):
    beau = beautify(data)
    data = cl.OrderedDict(data)

    aprint(bold(worker.id), "task", pos, "=>", beau, aqueue = aqueue)

    start = time.time()
    config.run(worker.id, data, pos)
    runtime = "({})".format(get_rt(time.time() - start))

    aprint(bold(worker.id), "done", pos, "=>", beau, runtime, aqueue = aqueue)

def wait (worker, busy, *, aqueue):
    printed = []
    unique = set()

    aprint(bold(worker.id), "wait", "{}s:".format(config.time_wait),
           "found", aqueue = aqueue, end = " ")

    for bid, wid in busy:
        if not config.unique_busy or wid not in unique:
            printed.append("{} <- {}".format(bold(wid), bid))
            unique.add(wid)

            if len(printed) >= config.max_busy:
                break

    aprint(*printed, ts = False, aqueue = aqueue, end = " ", sep = ", ")

    if len(busy) > len(printed):
        diff = "... +{}".format(len(busy) - len(printed))
        aprint(diff, ts = False, aqueue = aqueue, end = " ")

    aprint("busy", ts = False, aqueue = aqueue)
    time.sleep(config.time_wait)

def end (worker, *, aqueue):
    aprint(bold(worker.id), "end", aqueue = aqueue)

def main (argv):
    aqueue = queue.Queue()

    logger = threading.Thread(target = async_printer, kwargs = {
        "fname": config.files.log, "aqueue": aqueue
    })

    logger.start()
    wrk = worker.worker()

    try:
        wrk.work(task, num_tasks = config.num_tasks,
                 begin = begin, starve = starve,
                 fetch = fetch, wait = wait, end = end,
                 tkwargs = { "aqueue": aqueue },
                 bkwargs = { "aqueue": aqueue },
                 skwargs = { "aqueue": aqueue },
                 fkwargs = { "aqueue": aqueue },
                 wkwargs = { "aqueue": aqueue },
                 ekwargs = { "aqueue": aqueue })

    except KeyboardInterrupt:
        pass

    print("ending")

    aqueue.put(None)
    logger.join()

if __name__ == "__main__":
    main(sys.argv[ 1 : ])
