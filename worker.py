#!/usr/bin/env python3

import os
import mmap
import time

import alist
import flock
import config
import util


def _default_wait (*_):
    time.sleep(config.wait_time)

def _no_op (*_):
    pass

class worker (object):

    __slots__ = [ "id", "data", "folder", "last_edit" ]

    def fix_size (self, file):
        data_path = self.data_path()
        mtime = os.path.getmtime(data_path)

        if mtime != self.last_edit:
            self.data = None
            self.data = alist.read(data_path)
            self.last_edit = mtime

        fsize = os.path.getsize(file.name)
        req_size = config.one_size * len(self.data)

        if fsize < req_size:
            file.seek(0, os.SEEK_END)

            for _ in range((req_size - fsize) // config.one_size):
                file.write(config.sep_free)

            alist.commit(file)

    def fetch_work (self, file, num_tasks):
        found = []
        has_work = False

        with mmap.mmap(file.fileno(), 0) as mem:
            found.extend(util.iter_free(mem, limit = num_tasks))

            for start, end in found:
                mem[ start + 1 : end ] = self.id_bytes

            if len(found) < num_tasks:
                for start, end in util.iter_work(mem):
                    oth_bytes = mem[ start + 1 : end ]
                    oth = int.from_bytes(oth_bytes, config.use_order)
                    add = oth == self.id

                    if not add:
                        oth_path = self.lock_path(oth)
                        alist.mkfile(oth_path)

                        with open(oth_path, "rb+") as oth_file:
                            try:
                                with flock.flock(oth_file, block = False):
                                    mem[ start + 1 : end ] = self.id_bytes
                                    add = True

                            except alist.LockedException:
                                has_work = True

                    if add:
                        found.append(( start, end ))

                        if len(found) >= num_tasks:
                            break

        has_work |= bool(found)
        return [ f[0] // config.one_size for f in found ], has_work

    def get_work (self, num_tasks):
        done_path = self.done_path()
        alist.mkfile(done_path)
        work = []
        has_work = False

        with open(done_path, "rb+") as file:
            with flock.flock(file):
                self.fix_size(file)
                work, has_work = self.fetch_work(file, num_tasks)

                if work:
                    alist.commit(file)

        return work, has_work

    def __init__ (self, folder):
        self.folder = folder
        self.last_edit = None

        wid_file = os.path.join(self.folder, config.wid_fname)
        alist.mkfile(wid_file)

        with open(wid_file, "rb+") as file:
            with flock.flock(file):
                file.seek(0, os.SEEK_SET)
                data = file.read(config.use_bytes)
                self.id = int.from_bytes(data, config.use_order) + 1

                file.seek(0, os.SEEK_SET)
                file.write(self.id_bytes)

                alist.commit(file)

    def mark_done (self, pos):
        with open(self.done_path(), "rb+") as file:
            with flock.flock(file):
                file.seek(pos * config.one_size + 1, os.SEEK_SET)
                file.write(config.done)

    def work (
        self, func, *, num_tasks = config.num_tasks,
        begin = _no_op, wait = _default_wait, end = _no_op,
        fargs = (), fkwargs = {}, bargs = (), bkwargs = {},
        wargs = (), wkwargs = {}, eargs = (), ekwargs = {}
    ):
        lock_path = self.lock_path(self.id)
        alist.mkfile(lock_path)

        with open(lock_path, "rb+") as file:
            begin(self, *bargs, **bkwargs)

            with flock.flock(file):
                while True:
                    indices, has_work = self.get_work(num_tasks)

                    if not indices:
                        if has_work:
                            wait(self, *wargs, **wkwargs)
                            continue

                        break

                    for pos in indices:
                        func(self, self.data[pos], pos, *fargs, **fkwargs)
                        self.mark_done(pos)

            end(self, *eargs, **ekwargs)

    def done_path (self):
        return os.path.join(self.folder, config.don_fname)

    def lock_path (self, wid):
        return os.path.join(self.folder, config.lock_path, str(wid))

    def data_path (self):
        return os.path.join(self.folder, config.dat_fname)

    @property
    def id_bytes (self):
        return self.id.to_bytes(config.use_bytes, config.use_order)


if __name__ == "__main__":

    import tempfile
    import multiprocessing as mp


    threads = 100

    def test (dirname):

        def work (worker, data, pos):
            print(wrk.id, "got", pos, "=", data)
            time.sleep((5 * wrk.id) / threads)
            print(wrk.id, "done", pos)

        def begin (wrk):
            print(wrk.id, "is begining")

        def wait (wrk):
            print(wrk.id, "is waiting 1s")
            time.sleep(1)

        def end (wrk):
            print(wrk.id, "is ending")

        wrk = worker(dirname)
        wrk.work(work, num_tasks = 1, begin = begin, wait = wait, end = end)

    dirname = tempfile.mkdtemp()
    alist.write(os.path.join(dirname, "queue"), *range(20))

    print("starting test")

    with mp.Pool(threads) as p:
        p.map(test, [ dirname ] * threads)

    print("ending test")
