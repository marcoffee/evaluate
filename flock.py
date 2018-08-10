import fcntl


class LockedException (Exception):
    pass

class flock (object):
    __slots__ = [ "file", "shared", "locked", "block" ]

    def lock (self, *, shared = None):
        shared = self.shared if shared is None else shared
        flg = fcntl.LOCK_SH if shared else fcntl.LOCK_EX

        fcntl.flock(self.file, flg)
        self.locked = True

    def try_lock (self, *, shared = None, throw = False):
        shared = self.shared if shared is None else shared
        flg = fcntl.LOCK_SH if shared else fcntl.LOCK_EX

        try:
            fcntl.flock(self.file, flg | fcntl.LOCK_NB)
            self.locked = True
        except OSError:
            if throw:
                raise LockedException

            return False

        return True

    def unlock (self):
        if self.locked:
            fcntl.flock(self.file, fcntl.LOCK_UN)
            self.locked = False

    def __init__ (self, file, shared = False, block = True):
        self.file = file
        self.shared = shared
        self.block = block
        self.locked = False

    def __del__ (self):
        self.unlock()

    def __enter__ (self, *_):
        self.lock() if self.block else self.try_lock(throw = True)

    def __exit__ (self, *_):
        self.unlock()
