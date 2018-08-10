#!/usr/bin/env python3

import io
import os
import sys
import queue
import shutil
import tempfile
import subprocess
import threading
import multiprocessing as mp

import config
import watch
import generate
import evaluate
import progress


def evaluate_thread (dirname, tid):
    real_stdout = sys.stdout
    real_stderr = sys.stderr

    sys.stdout = open(os.path.join(dirname, "{}.out".format(tid)), "w")
    sys.stderr = sys.stdout

    evaluate.main([])

    sys.stdout.close()
    sys.stderr = real_stderr
    sys.stdout = real_stdout

def progress_thread ():
    progress.main([ "-refresh", "1" ])

def watch_function ():
    prog = progress.main([ "-report", "-no-print" ])
    tail = subprocess.run(
        [ "tail", "-n", "20", config.files.log ],
        stdout = subprocess.PIPE, stderr = subprocess.STDOUT,
        universal_newlines = True
    )

    return "{}\n\n{}".format(prog, tail.stdout)

def watch_stop (wqueue):
    def func ():
        value = False

        try:
            value = wqueue.get(False)
        except queue.Empty:
            pass

        return value

    return func

def watch_thread (wqueue):
    watch.watch(watch_function, run_until = watch_stop(wqueue))

def main ():
    dirname = tempfile.mkdtemp(prefix = "test_", dir = ".")
    config.set_task_path(dirname)

    config.defaults = [
        ( "param1"   , "a" ),
        ( "-param2"  , 1 ),
        ( "-param3"  , 1.0 ),
        ( "-param4"  , "a 1 1.0" ),
        ( "-param5"  , config.ENABLE ),
        ( "-param6"  , "fixed" ),
        ( "-param7"  , "1" )
    ]

    config.tests = [(
        ( "param1"   , [ "a", "b", "c", "d", "e" ] ),
        ( "-param2"  , [ 1, 2, 3, 4, 5 ] ),
        ( "-param3"  , [ 1.0, 1.1, 1.2, 1.3, 1.4 ] ),
        ( "-param4"  , [ "1 2 3", "a b c", "1 a bla" ] ),
        ( "-param5"  , [ config.ENABLE, config.DISABLE ] ),
        ( "-param7"  , [ "1", "2", "3" ] ),
    ), (
        ( "param1"   , [ "e", "f", "g", "h" ] ),
        ( "-param2"  , [ 1, 2, 3, 4, 5 ] ),
        ( "-param3"  , [ 1.0, 1.5, 2.0, 2.5, 3.0 ] ),
        ( "-param4"  , [ "1 2 3", "a b c", "1 a bla" ] ),
        ( "-param5"  , [ config.ENABLE, config.DISABLE ] ),
        ( "-param7"  , [ "1", "2", "4" ] ),
    )]

    eval_path = os.path.join(dirname, "evals")
    os.makedirs(eval_path, exist_ok = True)

    workers = []

    generate.main([])

    prog = mp.Process(target = progress_thread)
    prog.start()

    wqueue = queue.Queue()

    wat = threading.Thread(target = watch_thread, args = ( wqueue, ))
    wat.start()

    for i in range(4):
        wrk = mp.Process(target = evaluate_thread, args = ( eval_path, i ))
        wrk.start()
        workers.append(wrk)

    try:
        prog.join()

        for wrk in workers:
            wrk.join()

        wqueue.put(True)
        wat.join()

    except KeyboardInterrupt:
        print()
        pass

    finally:
        prog.terminate()

        for wrk in workers:
            wrk.terminate()

        wqueue.put(True)
        wat.join()

        print("test saved to", dirname)

if __name__ == "__main__":
    main()
