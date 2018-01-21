#!/usr/bin/env python3

import os
import shutil
import testconfig


paths = [
    testconfig.rst_path, testconfig.plt_path, testconfig.deq_path,
    testconfig.tre_path, testconfig.tst_file, testconfig.siz_file
]

for path in paths:
    size = 0
    stat = ""
    dele = lambda *_: None

    if os.path.isfile(path):
        dele = os.remove
        size = os.stat(path).st_size

        if size > 0:
            stat = "{} bytes".format(size)

    elif os.path.isdir(path):
        dele = shutil.rmtree
        size = 0

        for _, _, files in os.walk(path):
            size += len(files)

            if size >= 1000:
                break

        if size > 0:
            stat = "{} files".format(str(size) if size < 1000 else "1000+")

    txt = "Delete '{}' ({}) (y / n)? ".format(path, stat)

    if size == 0 or input(txt).upper() == "Y":
        dele(path)
