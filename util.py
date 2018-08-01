import re
import math

import config


re_work = re.compile(
    config.sep_byte + b"(?!" + config.done + b")" + (b"." * config.use_bytes)
)

def next_bytes (mem, byt, start = 0, end = None):
    end = len(mem) if end is None else end
    res = mem.find(byt, start, end)

    if res == -1:
        return None

    return res, res + config.one_size

def iter_bytes (mem, byt, start = 0, end = None, limit = math.inf):
    end = len(mem) if end is None else end
    count = 0

    while count < limit:
        pos = next_bytes(mem, byt, start, end)

        if pos is None:
            break

        yield pos
        start = pos[1]
        count += 1

def next_free (mem, start = 0, end = None):
    return next_bytes(mem, config.sep_free, start, end)

def next_done (mem, start = 0, end = None):
    return next_bytes(mem, config.sep_done, start, end)

def iter_free (mem, start = 0, end = None, limit = math.inf):
    yield from iter_bytes(mem, config.sep_free, start, end, limit)

def iter_done (mem, start = 0, end = None, limit = math.inf):
    yield from iter_bytes(mem, config.sep_done, start, end, limit)

def next_work (mem, start = 0, end = None):
    end = len(mem) if end is None else end
    mat = re_work.search(mem, start)

    if mat is None:
        return None

    return mat.span()

def iter_work (mem, start = 0, end = None, limit = math.inf):
    end = len(mem) if end is None else end
    count = 0
    found = iter(re_work.finditer(mem, start, end))

    while count < limit:
        try:
            pos = next(found).span()
        except StopIteration:
            break

        yield pos
        start = pos[1]
        count += 1
