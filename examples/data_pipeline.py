"""Realistic workload script for profiling and demonstrating FlameLens features."""


class SessionCache:
    def __init__(self):
        self._cache = {}

    def populate(self, count: int = 150):
        for i in range(count):
            self._cache[f"session_{i}"] = {
                "token": "tok_" + str(i),
                "buffer": b"S" * 32768,  # 32 KB per entry
                "metadata": {"ttl": 3600, "user_id": i},
            }


class PayloadDecoder:
    def decode_stream(self, batches: int = 80):
        results = []
        for b in range(batches):
            chunk = b"RECORD_PAYLOAD_DATA_" * 1500  # ~30 KB per chunk
            decoded = chunk.decode("ascii")
            results.append(decoded)
        return results


class DataPipeline:
    def __init__(self):
        self.cache = SessionCache()
        self.decoder = PayloadDecoder()

    def run(self):
        self.cache.populate(120)
        _ = self.decoder.decode_stream(100)


if __name__ == "__main__":
    pipeline = DataPipeline()
    pipeline.run()
