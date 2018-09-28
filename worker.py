#!/usr/bin/env python3

import os
import mmap
import time
import itertools as it

import alist
import flock
import config
import starvation
import util


def _default_wait (*_):
    time.sleep(config.time_wait)

def _no_op (*_):
    pass

class worker (object):

    __slots__ = [ "id", "data", "last_edit" ]

    def fix_size (self, file):
        mtime = os.path.getmtime(config.files.data)

        if mtime != self.last_edit:
            self.data = None
            self.data = alist.read(config.files.data)
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
        reason = []
        busy = []

        with mmap.mmap(file.fileno(), 0) as mem:
            for start, end in util.iter_free(mem, limit = num_tasks):
                reason.append(( "free", 0 ))
                found.append(start // config.one_size)
                mem[ start + 1 : end ] = self.id_bytes

            if len(found) < num_tasks:
                for start, end in util.iter_work(mem):
                    oth_bytes = mem[ start + 1 : end ]
                    oth = int.from_bytes(oth_bytes, config.use_order)
                    add = oth == self.id
                    rea = "mine"

                    if not add:
                        oth_path = self.lock_path(oth)
                        alist.mkfile(oth_path)

                        with open(oth_path, "rb+") as oth_file:
                            try:
                                with flock.flock(oth_file, block = False):
                                    mem[ start + 1 : end ] = self.id_bytes
                                    add = True
                                    rea = "dead"

                            except flock.LockedException:
                                busy.append(( start // config.one_size, oth ))

                    if add:
                        found.append(start // config.one_size)
                        reason.append(( rea, oth ))

                        if len(found) >= num_tasks:
                            break

        return found, reason, busy

    def get_work (self, num_tasks):
        alist.mkfile(config.files.done)
        found = []
        busy = []

        with open(config.files.done, "rb+") as file:
            with flock.flock(file):
                self.fix_size(file)

                found, reason, busy = self.fetch_work(file, num_tasks)

                if found:
                    alist.commit(file)

        return found, reason, busy

    def __init__ (self):
        self.last_edit = None
        alist.mkfile(config.files.wid)

        with open(config.files.wid, "rb+") as file:
            with flock.flock(file):
                file.seek(0, os.SEEK_SET)
                data = file.read(config.use_bytes)
                self.id = int.from_bytes(data, config.use_order) + 1

                file.seek(0, os.SEEK_SET)
                file.write(self.id_bytes)

                alist.commit(file)

    def mark_done (self, pos):
        with open(config.files.done, "rb+") as file:
            with mmap.mmap(file.fileno(), 0) as mem:
                fpos = pos * config.one_size
                mem[ fpos : fpos + config.one_size ] = config.sep_done

    def work (
        self, task, *, num_tasks = config.num_tasks,
        begin = _no_op, starve = _no_op, fetch = _no_op,
        wait = _default_wait, end = _no_op,
        targs = (), tkwargs = {}, bargs = (), bkwargs = {},
        sargs = (), skwargs = {}, fargs = (), fkwargs = {},
        wargs = (), wkwargs = {}, eargs = (), ekwargs = {}
    ):
        lock_path = self.lock_path(self.id)
        alist.mkfile(lock_path)
        done = []

        starve_func = lambda amount: starve(self, amount, *sargs, **skwargs)
        starve_check = starvation.checker(starve_func, config.time_starve)

        with open(lock_path, "rb+") as file:
            with flock.flock(file):
                begin(self, *bargs, **bkwargs)
                found = reason = busy = None

                while True:
                    with starve_check:
                        found, reason, busy = self.get_work(num_tasks)

                    if not found:
                        if not busy:
                            break

                        wait(self, busy, *wargs, **wkwargs)
                        continue

                    fetch(self, found, reason, *fargs, **fkwargs)

                    if len(self.data) > len(done):
                        diff = len(self.data) - len(done)
                        done.extend(it.repeat(False, diff))

                    for pos, rea in zip(found, reason):
                        if not done[pos]:
                            data = self.data[pos]
                            task(self, data, pos, rea, *targs, **tkwargs)
                            done[pos] = True

                        self.mark_done(pos)

            end(self, *eargs, **ekwargs)

    def lock_path (self, wid):
        return os.path.join(config.paths.lock, str(wid))

    @property
    def id_bytes (self):
        return self.id.to_bytes(config.use_bytes, config.use_order)
