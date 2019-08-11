# coding=utf-8

import asyncio
import time


class GatherTask:
    NO_RESULT = object()

    def __init__(self, n, early_stop=False):
        self.early_stop = early_stop
        self._done = asyncio.Future()
        self.result = []
        for i in range(n):
            self.result.append(self.NO_RESULT)
        self.completed = 0
        self.start_time = None
        self.log_time = []

    async def _complete_delay(self, timeout):
        await asyncio.sleep(timeout)
        if not self.is_done():
            self._done.set_result(True)

    async def done(self, timeout=None):
        if timeout is not None:
            asyncio.ensure_future(self._complete_delay(timeout))
        self.start_time = time.time()
        await self._done

    def is_done(self):
        return self._done.done()

    def set_result(self, index, result=None):
        assert 0 <= index < len(self.result)
        if not self.is_done():
            self.result[index] = result
            self.completed += 1
            if self.completed >= len(self.result):
                self._done.set_result(True)
            else:
                if self.early_stop:
                    self._try_early_stop()

    def _try_early_stop(self):
        self.log_time.append(time.time())
        if len(self.log_time) / len(self.result) > 0.5:
            avg = 0
            for t in self.log_time:
                avg += t - self.start_time
            avg /= len(self.log_time)
            asyncio.ensure_future(self._complete_delay(avg))

    def update_result(self, index, result):
        assert 0 <= index < len(self.result)
        if not self.is_done():
            self.result[index] = result
