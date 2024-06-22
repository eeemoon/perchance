import time


class timeout:
    def __init__(self, seconds: float, exc: Exception | None = None):
        self._exc = exc or TimeoutError()
        self._timeout = time.time() + seconds

    async def __aenter__(self) -> "timeout":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def tick(self):
        if time.time() > self._timeout:
            raise self._exc
