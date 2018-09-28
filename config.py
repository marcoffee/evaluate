import os
import time
import glob
import subprocess
import collections as cl

from defines import *


set_task_path("task")

num_tasks = 50
time_wait = 15
time_starve = 15

max_busy = 5
max_recv = 15

unique_busy = True

ts_format = "%H:%M:%S"
rt_format = "%H:%M:%S"
colors = "034", "056", "142", "126", "117", "088", "022", "069", "053", "181"

recv_free = "070"
recv_mine = "178"
recv_dead = "124"

defaults = [
    ( "param1"   , "a" ),
    ( "-param2"  , 1 ),
    ( "-param3"  , 1.0 ),
    ( "-param4"  , [ "a", 1, 1.0 ] ),
    ( "-param5"  , ENABLE ),
    ( "-param6"  , "fixed" ),
    ( "-param7"  , "1" )
]

tests = [(
    ( "param1"   , [ "a", "b", "c", "d", "e" ] ),
    ( "-param2"  , [ 1, 2, 3, 4, 5 ] ),
    ( "-param3"  , [ 1.0, 1.1, 1.2, 1.3, 1.4 ] ),
    ( "-param4"  , [ [ 1, 2, 3 ], [ "a", "b", "c" ], [ 1, "a", False ] ] ),
    ( "-param5"  , [ ENABLE, DISABLE ] ),
    ( "-param7"  , [ "1", "2", "3" ] ),
), (
    ( "param1"   , [ "e", "f", "g", "h" ] ),
    ( "-param2"  , [ 1, 2, 3, 4, 5 ] ),
    ( "-param3"  , [ 1.0, 1.5, 2.0, 2.5, 3.0 ] ),
    ( "-param4"  , [ [ 1, 2, 3 ], [ "a", "b", "c" ], [ 1, "a", True ] ] ),
    ( "-param5"  , [ ENABLE, DISABLE ] ),
    ( "-param7"  , [ "1", "2", "4" ] ),
)]

def ignore (flags):
    if flags["param1"] == "e" and flags["-param5"] == DISABLE:
        return True

    return False

def preprocess (key, val):
    pass

def log_format (key, val):
    if key == "-param7":
        yield "{}={}".format(key, val)

    elif val is ENABLE:
        yield key

    elif val is DISABLE:
        yield "[{}]".format(key)

    else:
        yield "{}: {}".format(key, val)

def param_format (key, val):
    if val is not DISABLE:
        if key == "-param7":
            yield "{}={}".format(key, val)

        else:
            if key[0] == "-":
                yield key

            if isinstance(val, list):
                for v in val:
                    yield str(v)

            elif val is not ENABLE:
                yield str(val)

def run (wid, data, pos):
    print(*(
        param for key, val in data.items() for param in param_format(key, val)
    ))

    time.sleep(0.1)
