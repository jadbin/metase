# coding=utf-8

import asyncio


class GatherTask:
    NO_RESULT = object()

    def __init__(self, n):
        self._done = asyncio.Future()
        self.result = []
        for i in range(n):
            self.result.append(self.NO_RESULT)
        self.completed = 0

    async def _complete_delay(self, timeout):
        await asyncio.sleep(timeout)
        if not self.is_done():
            self._done.set_result(True)

    async def done(self, timeout=None):
        if timeout is not None:
            asyncio.ensure_future(self._complete_delay(timeout))
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

    def update_result(self, index, result):
        assert 0 <= index < len(self.result)
        if not self.is_done():
            self.result[index] = result
