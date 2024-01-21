from queue import PriorityQueue


class LockedPriorityQueue(PriorityQueue):
    def __init__(self, *args, **kwargs):
        super(LockedPriorityQueue, self).__init__(*args, **kwargs)
        self.locked = True

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def put(self, *args, **kwargs):
        if self.locked:
            raise Exception("Queue is locked. Cannot add items.")
        else:
            super().put(*args, **kwargs)
