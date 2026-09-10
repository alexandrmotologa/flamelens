"""Synthetic application for profiling and leak detection testing."""


class SessionCache:
    def __init__(self):
        self.data = []

    def add_session(self, size_kb=200):
        # Leaking buffer: retained in cache
        self.data.append(bytearray(size_kb * 1024))


def handle_order(cache, order_id):
    cache.add_session(300)
    # Temporary buffer: quickly discarded
    temp = bytearray(100 * 1024)
    return len(temp)


def main():
    cache = SessionCache()
    for i in range(5):
        handle_order(cache, i)


if __name__ == "__main__":
    main()
