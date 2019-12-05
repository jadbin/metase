# coding=utf-8

import asyncio
import time


class GatherTask:
    NO_RESULT = object()

    def __init__(self, n, early_stop=False, timeout=None):
        self._done = asyncio.Future()
        self.result = []
        for i in range(n):
            self.result.append(self.NO_RESULT)
        self.completed = 0
        self.early_stop = early_stop
        self.timeout = timeout
        self.start_time = None
        self.task_log = []
        self._early_stop_future = None

    async def _complete_delay(self, timeout):
        await asyncio.sleep(timeout)
        if not self.is_done():
            self._done.set_result(True)

    async def done(self):
        if self.timeout is not None:
            asyncio.ensure_future(self._complete_delay(self.timeout))
        self.start_time = time.time()
        await self._done

    def is_done(self):
        return self._done.done()

    def set_result(self, index, result=None):
        assert 0 <= index < len(self.result)
        if not self.is_done():
            self.task_log.append(dict(index=index, completed_time=time.time()))
            self.result[index] = result
            self.completed += 1
            if self.completed >= len(self.result):
                self._done.set_result(True)
            else:
                if self.early_stop:
                    self._try_early_stop()

    def _try_early_stop(self):
        if len(self.task_log) / len(self.result) >= 0.8:
            max_t = 0
            for t in self.task_log:
                max_t = max(max_t, t['completed_time'] - self.start_time)
            if self.timeout:
                max_t = max(max_t, self.timeout / 4)
            if self._early_stop_future is None:
                self._early_stop_future = asyncio.ensure_future(self._complete_delay(max_t))

    def update_result(self, index, result):
        assert 0 <= index < len(self.result)
        if not self.is_done():
            self.result[index] = result
