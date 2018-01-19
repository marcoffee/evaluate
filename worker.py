#!/usr/bin/env python3

import os
import time
import adeque


class WorkerException (Exception):
    pass

def _default_wait (_):
    time.sleep(10)

def _no_op (_):
    pass

class Worker (object):

    _status_exit = 0
    _status_wait = 1
    _status_next = 2
    _status_none = 3

    def __init__ (self, deque, path = "."):
        path = os.path.realpath(path)
        os.makedirs(path, exist_ok = True)

        self.__worker_path = os.path.join(path, "workers")
        os.makedirs(self.__worker_path, exist_ok = True)

        self.__id_file = os.path.join(path, "id")

        with adeque.LockFile(self.id_file, "a+") as file:
            file.rewind()
            self.__id = int(file.readline().strip() or 1)
            file.clear()
            print(self.id + 1, file = file, flush = True)

        self.__lock_path = os.path.join(self.__worker_path, str(self.id))
        self.__lock = adeque.LockFile(self.__lock_path, "w")

        self.__deque = adeque.Deque(deque, path)

    def __del__ (self):
        self.free()

    def free (self):
        self.__deque.free()
        self.__lock.free()

        try:
            os.remove(self.__lock_path)
        except FileNotFoundError:
            pass

    def work_one (self, func, fkwargs = {}):
        sid = selected = None

        with self.__deque:
            if len(self.__deque) == 0:
                return Worker._status_exit

            for i, ( owner, tid, task ) in enumerate(self.__deque):
                free = owner is None or owner == self.id

                if not free:
                    fname = os.path.join(self.__worker_path, str(owner))
                    lock = None

                    try:
                        lock = adeque.LockFile(fname, "r+")
                        free = lock.trylock()

                        if free:
                            lock.free()

                    except FileNotFoundError:
                        free = True

                    finally:
                        lock and lock.free()

                if free:
                    sid = tid
                    selected = task

                    self.__deque.remove(i)
                    self.__deque.push(( self.id, sid, selected ))

                    break

            else:
                return Worker._status_wait

        func(self, sid, selected, **fkwargs)

        with self.__deque:
            for i, ( owner, tid, task ) in enumerate(self.__deque):
                if tid == sid:
                    self.__deque.remove(i)
                    break

        return Worker._status_next

    def work (self, func, fkwargs = {},
              begin = _no_op, wait = _default_wait, end = _no_op):
        try:
            begin(self)

            while True:
                result = Worker._status_none

                with self.__lock:
                    result = self.work_one(func, fkwargs = fkwargs)

                if result == Worker._status_wait:
                    wait(self)

                elif result == Worker._status_exit:
                    break

                elif result == Worker._status_none:
                    raise WorkerException("Unable to work or lock file.")

        finally:
            end(self)

    @property
    def id (self):
        return self.__id

    @property
    def id_file (self):
        return self.__id_file

if __name__ == '__main__':

    import random
    import tempfile
    import itertools as it
    import multiprocessing as mp

    def test (dirname):

        def work (worker, tid, val):
            print(worker.id, "got", tid, "=", val)
            time.sleep(val)
            print(worker.id, "done", tid)

        def begin (worker):
            print(worker.id, "is begining")

        def wait (worker):
            print(worker.id, "is waiting 1s")
            time.sleep(1)

        def end (worker):
            print(worker.id, "is ending")

        worker = Worker("worker", dirname)
        worker.work(work, begin = begin, wait = wait, end = end)

    dirname = tempfile.mkdtemp()

    deque = adeque.Deque("worker", dirname)
    deque.push(*zip(
        it.repeat(None), it.count(1),
        [ 10, 1, 2, 5, 1, 1, 1, 5, 3, 1, 1, 4 ]
    ))
    deque.free()

    print("starting test")

    with mp.Pool(3) as p:
        p.map(test, [ dirname ] * 3)

    print("ending test")
