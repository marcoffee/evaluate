import os
import collections as cl


ENABLE = True
DISABLE = False

use_bytes = 2
use_order = "little"
pro_format = "<QQQd"

sep_byte = b"\xaa"
free_byte = b"\x00"
done_byte = b"\xff"

free = free_byte * use_bytes
done = done_byte * use_bytes

sep_free = sep_byte + free
sep_done = sep_byte + done

one_size = len(sep_byte) + use_bytes

class paths_t (object):
    __slots__ = [ "task", "lock" ]

class files_t (object):
    __slots__ = [ "wid", "done", "data", "log", "progress" ]

paths = paths_t()
files = files_t()

def set_task_path (path):
    global paths
    global files

    paths.task = os.path.realpath(path)
    paths.lock = os.path.join(paths.task, "locks")

    files.wid = os.path.join(paths.task, "id")
    files.done = os.path.join(paths.task, "done")
    files.data = os.path.join(paths.task, "queue")
    files.log = os.path.join(paths.task, "log.out")
    files.progress = os.path.join(paths.task, "progress")
