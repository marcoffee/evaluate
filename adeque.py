import os
import re
import fcntl
import pickle
import base64
import hashlib
import inspect
import unicodedata
import traceback as tb
import itertools as it


def maps (ite, func, *funcs):
    ite = map(func, ite)

    for func in funcs:
        ite = map(func, ite)

    return ite

class LockFileBaseException (Exception):
    pass

class UnlockedException (LockFileBaseException):
    pass

class LockedException (LockFileBaseException):
    pass

class LockFile (object):

    def __init__ (self, *args, **kwargs):
        self.__file = open(*args, **kwargs)

        self.tell = self.__file.tell
        self.seek = self.__file.seek
        self.read = self.__file.read
        self.readline = self.__file.readline
        self.readlines = self.__file.readlines
        self.readable = self.__file.readable
        self.close = self.__file.close
        self.fileno = self.__file.fileno

        self.__attrs = {
            n: m for n, m in inspect.getmembers(self.__file, inspect.isroutine)
                if not (n.startswith("_") or hasattr(self, n))
        }

        self.__lock_count = 0
        self._disable()

    def __del__ (self):
        self.free()

    def __enter__ (self):
        self.lock()
        return self

    def __exit__ (self, *_):
        self.unlock()

    def __next__ (self):
        return next(self.__file)

    def __iter__ (self):
        for line in self.__file:
            yield line

    @staticmethod
    def _raise_unlocked (*_):
        raise UnlockedException("Unlocked file.")

    def _enable (self):
        for name, meth in self.__attrs.items():
            setattr(self, name, meth)

    def _disable (self):
        for name in self.__attrs.keys():
            setattr(self, name, LockFile._raise_unlocked)

    def rewind (self):
        return self.seek(0, os.SEEK_SET)

    def clear (self):
        self.rewind()
        self.truncate()

    def force_flush (self):
        self.flush()
        os.fsync(self.fileno())

    def free (self):
        if not self.closed:
            self.unlock()
            self.close()

    def lock (self, wait = True, recursive = True):
        if not self.locked:
            flags = fcntl.LOCK_EX

            if not wait:
                flags |= fcntl.LOCK_NB

            fcntl.flock(self.fileno(), flags)
            self._enable()

        elif not recursive:
            raise LockedException("File already locked.")

        self.__lock_count += 1

    def unlock (self, clearall = False):
        if self.locked:
            if clearall:
                self.__lock_count = 0
            else:
                self.__lock_count -= 1

            if self.__lock_count == 0:
                self.force_flush()
                fcntl.flock(self.fileno(), fcntl.LOCK_UN)
                self._disable()

            return True

        return False

    def trylock (self, recursive = True):
        try:
            self.lock(wait = False, recursive = recursive)

        except ( BlockingIOError, LockedException ):
            return False

        else:
            return True

    @property
    def lock_count (self):
        return self.__lock_count

    @property
    def locked (self):
        return self.lock_count > 0

    @property
    def closed (self):
        return self.__file.closed

    @property
    def name (self):
        return self.__file.name

class Deque (object):

    _no_stop = object()
    _re_sanitize = re.compile(r"[^a-zA-Z0-9\-]+")

    @staticmethod
    def _decode_one (value):
        return pickle.loads(base64.a85decode(value.encode("ascii")))

    @staticmethod
    def _decode (data, slc):
        if isinstance(slc, slice):
            return [ Deque._decode_one(v) for v in data[slc] ]

        return Deque._decode_one(data[slc])

    def __init__ (self, name, path = "."):
        path = os.path.realpath(path)
        os.makedirs(path, exist_ok = True)

        enco = base64.urlsafe_b64encode(hashlib.md5(name.encode()).digest())
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore")
        name = Deque._re_sanitize.sub("_", name.decode())

        fname = "{}.{}.deq".format(name[ : 5 ], enco.decode()[ : -2 ])

        self.__fname = os.path.join(path, fname)
        self.__file = None
        self.__mtime = None
        self.__data = None

    def __del__ (self):
        self.free()

    def __enter__ (self):
        self.onatomic()
        return self

    def __exit__ (self, *_):
        self.offatomic()

    def __getitem__ (self, pos):
        if isinstance(pos, slice):
            return self.peek(pos.start, pos.stop, pos.step)

        return self.peek(pos)

    def __delitem__ (self, pos):
        if isinstance(pos, slice):
            self.remove(pos.start, pos.stop, pos.step)
        else:
            self.remove(pos)

    def __str__ (self):
        return "Deque({{{}}})".format(", ".join(map(str, self)))

    def __repr__ (self):
        return str(self)

    def __len__ (self):
        self._fetch_list()
        return len(self.__data)

    def __iter__ (self):
        self._fetch_list()

        for i in range(len(self.__data)):
            yield Deque._decode(self.__data, i)

    def _get_file (self):
        if not self.is_atomic:
            return LockFile(self.__fname, "a+")

        return self.__file

    def _fetch_list (self):
        file = self._get_file()
        mtime = os.stat(file.fileno()).st_mtime_ns

        if mtime != self.__mtime:
            file.rewind()
            self.__data = [ x.strip() for x in file ]
            self.__mtime = mtime

    def free (self):
        self.offatomic(clearall = True)

    def onatomic (self, wait = True, recursive = True):
        self.__file = self._get_file()
        self.__file.lock(wait = wait, recursive = recursive)

    def offatomic (self, clearall = False):
        if self.is_atomic:
            self.__file.unlock(clearall = clearall)

            if not self.__file.locked:
                self.__file.free()
                self.__file = None

    def clear (self, wait = True):
        try:
            self.onatomic(wait = wait, recursive = True)
            self.__file.clear()

        finally:
            self.offatomic(clearall = False)

    def remove (self, start = 0, stop = _no_stop, step = 1, wait = True):
        one = stop is Deque._no_stop

        if one:
            stop = (start + 1) or None

        atomic = self.__file is not None

        try:
            self.onatomic(wait = wait, recursive = True)
            self._fetch_list()

            slc = slice(start, stop, step)

            self.__file.clear()
            del self.__data[slc]

            if self.__data:
                print(*self.__data,
                      sep = "\n", file = self.__file, flush = True)

                self.__mtime = os.stat(self.__file.fileno()).st_mtime_ns

        finally:
            self.offatomic(clearall = False)

    def pop (self, start = 0, stop = _no_stop, step = 1, default = None, wait = True):
        one = stop is Deque._no_stop

        if one:
            stop = (start + 1) or None

        try:
            self.onatomic(wait = wait, recursive = True)
            self._fetch_list()

            slc = slice(start, stop, step)
            items = Deque._decode(self.__data, slc)

            self.__file.clear()
            del self.__data[slc]

            if self.__data:
                print(*self.__data,
                      sep = "\n", file = self.__file, flush = True)

                self.__mtime = os.stat(self.__file.fileno()).st_mtime_ns

            if one:
                items = items[0] if items else default

            return items

        finally:
            self.offatomic(clearall = False)

    def peek (self, start = 0, stop = _no_stop, step = 1, default = None):
        one = stop is Deque._no_stop

        if one:
            stop = (start + 1) or None

        self._fetch_list()

        slc = slice(start, stop, step)
        items = Deque._decode(self.__data, slc)

        if one:
            items = items[0] if items else default

        return items

    def push (self, *items, wait = True):
        if not items:
            return

        try:
            self.onatomic(wait = wait, recursive = True)
            self.__file.seek(0, os.SEEK_END)

            print(*maps(items, pickle.dumps, base64.a85encode, bytes.decode),
                  sep = "\n", file = self.__file, flush = True)

        finally:
            self.offatomic(clearall = False)

    @property
    def atomic_levels (self):
        return int(self.__file is not None and self.__file.lock_count)

    @property
    def is_atomic (self):
        return self.atomic_levels > 0
