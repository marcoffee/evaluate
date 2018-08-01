import os
import time
import glob
import subprocess
import collections as cl


ENABLE = True
DISABLE = False

def build_params (data):
    for key, val in data.items():
        if val is DISABLE:
            continue

        if key[0] == "-":
            yield key

        if val is not ENABLE:
            yield str(val)

use_bytes = 2
use_order = "little"
colors = "034", "056", "142", "126", "117", "088", "069", "053", "181", "022"

work_path = "task"
lock_path = "locks"
wid_fname = "id"
dat_fname = "queue"
don_fname = "done"

sep_byte = b"\xaa"
free_byte = b"\x00"
done_byte = b"\xff"

free = free_byte * use_bytes
done = done_byte * use_bytes

sep_free = sep_byte + free
sep_done = sep_byte + done

one_size = len(sep_byte) + use_bytes

num_tasks = 15
wait_time = 10

log_fname = os.path.join(work_path, "log.out")
pro_fname = os.path.join(work_path, "progress.txt")

defaults = (
    ( "param1"      , "a" ),
    ( "-param2"     , 1 ),
    ( "-param3"     , 1.0 ),
    ( "-param4"     , "a 1 1.0" ),
    ( "-param5"     , ENABLE ),
)

tests = [(
    ( "param1"      , [ "a", "b", "c", "d" ] ),
    ( "-param2"     , [ 1, 2, 3, 4, 5 ] ),
    ( "-param3"     , [ 1.0, 1.1, 1.2, 1.3, 1.4 ] ),
    ( "-param4"     , [ "1 2 3", "a b c", "1 a bla" ] ),
    ( "-param5"     , [ ENABLE, DISABLE ] )
), (
    ( "param1"      , [ "e", "f", "g", "h" ] ),
    ( "-param2"     , [ 1, 2, 3, 4, 5 ] ),
    ( "-param3"     , [ 1.0, 1.5, 2.0, 2.5, 3.0 ] ),
    ( "-param4"     , [ "1 2 3", "a b c", "1 a bla" ] ),
    ( "-param5"     , [ ENABLE, DISABLE ] )
)]

def ignore (flags):
    if flags["param1"] == "e" and flags["-param5"] == DISABLE:
        return True

    return False

def run (flags):
    print(*build_params(flags))
    time.sleep(0.1)

def preprocess (key, val):
    pass

def log_format (key, val):
    if val is ENABLE:
        return key

    elif val is DISABLE:
        return "[{}]".format(key)

    return "{} = {}".format(key, val)
