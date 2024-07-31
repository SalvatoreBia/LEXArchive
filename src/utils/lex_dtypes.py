import threading
from collections import deque

class BlockingQueue:

    def __init__(self, size):
        self.size = size
        self.q = deque()
        self.lock = threading.RLock()
        self.get_cond = threading.Condition(self.lock)
        self.put_cond = threading.Condition(self.lock)

    def put(self, val):
        with self.lock:
            while len(self.q) == self.size:
                self.put_cond.wait()

            self.q.append(val)
            self.get_cond.notify_all()

    def get(self):
        with self.lock:
            while len(self.q) == 0:
                self.get_cond.wait()

            val = self.q.popleft()
            self.put_cond.notify_all()

            return val
