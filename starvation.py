import enum
import queue
import threading


class command (enum.Enum):
    START = 0
    STOP = 1
    END = 2

def check_thread (wait, aqueue, func):
    while True:
        value = aqueue.get()
        amount = 0

        while value is command.START:
            try:
                value = aqueue.get(timeout = wait)
            except queue.Empty:
                func(amount)
                amount += 1

        if value is command.END:
            break

class checker (object):

    __slots__ = [ "thread", "aqueue" ]

    def __init__ (self, func, wait):
        self.aqueue = queue.Queue()

        self.thread = threading.Thread(target = check_thread, kwargs = {
            "wait": wait, "aqueue": self.aqueue, "func": func
        })

        self.thread.start()

    def check (self):
        self.aqueue.put(command.START)

    def uncheck (self):
        self.aqueue.put(command.STOP)

    def end (self):
        self.aqueue.put(command.END)
        self.thread.join()

    def __enter__ (self, *_):
        self.check()

    def __exit__ (self, *_):
        self.uncheck()

    def __del__ (self):
        self.end()
