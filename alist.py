import os
import pickle
import flock


def mkfile (*names):
    for fname in map(os.path.realpath, names):
        if not os.path.exists(fname):
            os.makedirs(os.path.dirname(fname), exist_ok = True)
            open(fname, "a").close()

def commit (file):
    file.flush()
    os.fsync(file.fileno())

def iterate_locked (file):
    while True:
        try:
            data = pickle.load(file)
            yield data
        except EOFError:
            break

def iterate (fname):
    with open(fname, "rb") as file:
        with flock.flock(file, True):
            yield from iterate_locked(file)

def read_locked (file):
    result = []

    while True:
        try:
            data = pickle.load(file)
            result.append(data)
        except EOFError:
            break

    return result

def read (fname):
    result = None

    with open(fname, "rb") as file:
        with flock.flock(file, True):
            file.seek(0, os.SEEK_SET)
            result = read_locked(file)

    return result

def write_locked (file, *data, flush = True):
    for value in data:
        pickle.dump(value, file)

    if flush:
        commit(file)

    return len(data)

def write (fname, *data, create = True):
    written = 0

    if create:
        mkfile(fname)

    with open(fname, "rb+") as file:
        with flock.flock(file):
            file.seek(0, os.SEEK_END)
            written = write_locked(file, *data)

    return written
