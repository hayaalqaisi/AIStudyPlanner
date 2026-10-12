from time import perf_counter

import psutil


class PerformanceMeasurement:
    """Measure elapsed time and local process RSS memory."""

    def __init__(self):
        self.process = psutil.Process()
        self.started_at = None
        self.memory_before_bytes = None
        self.memory_after_bytes = None
        self.duration_ms = None

    def __enter__(self):
        if self.started_at is not None:
            raise ValueError("Use a new measurement for each operation.")

        self.memory_before_bytes = self.process.memory_info().rss
        self.started_at = perf_counter()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.finish()
        return False

    def finish(self):
        """Finish once, including when called before saving a log."""
        if self.started_at is None:
            raise ValueError("The measurement has not started yet.")

        if self.duration_ms is None:
            self.duration_ms = max(
                0,
                round((perf_counter() - self.started_at) * 1000),
            )
            self.memory_after_bytes = self.process.memory_info().rss

        return self.as_dict()

    def as_dict(self):
        """Return measurements after the operation has finished."""
        if self.duration_ms is None:
            raise ValueError("The measurement has not finished yet.")

        return {
            "duration_ms": self.duration_ms,
            "memory_before_bytes": self.memory_before_bytes,
            "memory_after_bytes": self.memory_after_bytes,
            "memory_delta_bytes": (
                self.memory_after_bytes - self.memory_before_bytes
            ),
        }