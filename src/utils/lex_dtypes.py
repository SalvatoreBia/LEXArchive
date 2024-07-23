import threading
from collections import deque


class BaseType:

    def __init__(self):
        pass

    def from_iterable(self, iterable):
        raise NotImplementedError("Subclasses should implement this method")


class Host(BaseType):

    def __init__(self, h=None, r=None, t=None):
        super().__init__()
        self.hostname = h
        self.radius = r
        self.temperature = t
        self._set_color()

    def _set_color(self):
        pass

    def from_iterable(self, iterable):
        try:
            self.hostname, self.radius, self.temperature = iterable
            self._set_color()
        except ValueError:
            raise ValueError("Iterable must have exactly 3 elements: hostname, radius, temperature")


class Planet(BaseType):
    def __init__(self, name=None, radius=None, semi_major_axis=None, eccentricity=None):
        super().__init__()
        self.name = name
        self.radius = radius
        self.semi_major_axis = semi_major_axis
        self.eccentricity = eccentricity

    def from_iterable(self, iterable):
        try:
            self.name, self.radius, self.semi_major_axis, self.eccentricity = iterable
        except ValueError:
            raise ValueError("Iterable must have exactly 4 elements: name, radius, semi_major_axis, eccentricity")


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

            if len(self.q) == self.size:
                self.get_cond.notify_all()

    def get(self):
        with self.lock:
            while len(self.q) == 0:
                self.get_cond.wait()

            val = self.q.popleft()

            if len(self.q) == self.size - 1:
                self.put_cond.notify_all()

            return val
