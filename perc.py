#!/usr/bin/env python3

import time
import testconfig
import collections as cl


def sec_to_str (sec):
    days, sec = divmod(sec, 86400)
    hours, sec = divmod(sec, 3600)
    minutes, sec = divmod(sec, 60)

    result = "{:>08.5f}".format(sec)

    if minutes or hours or days:
        result = "{:>02.0f}:{}".format(minutes, result)

        if hours or days:
            result = "{:>02.0f}:{}".format(hours, result)

            if days:
                result = "{:.0f}-{}".format(days, result)

    return result

count = None

with open("exp-size.txt") as file:
    count = int(file.readline())

start_time = time.time()
first_size = 0

try:
    while True:
        size = 0

        with open(testconfig.tst_file) as file:
            size = sum(1 for _ in file)

        first_size = first_size or size
        delta = size - first_size

        percentage = 100 * size / count
        per_sec = delta / (time.time() - start_time)
        eta = sec_to_str((count - size) / per_sec) if per_sec else "-"

        print("\033[K\r""{0:.0f}% => {0:.2f}% ({1:.2f} / s) ETA: {2}".format(
            percentage, per_sec, eta
        ), end = "")
        time.sleep(1)

except KeyboardInterrupt:
    pass

print()
