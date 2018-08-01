import os


ENABLE = True
DISABLE = False

work_path = "task"
lock_path = "locks"
wid_fname = "id"
dat_fname = "queue"
don_fname = "done"

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

log_fname = os.path.join(work_path, "log.out")
pro_fname = os.path.join(work_path, "progress.txt")
