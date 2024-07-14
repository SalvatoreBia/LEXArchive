class Host:

    def __init__(self, r, t):
        self.radius = r
        self.temperature = t
        self._set_color()

    def _set_color(self):
        pass


class Planet:
    def __init__(self, r, a):
        self.radius = r
        self.semi_major_axis = a
