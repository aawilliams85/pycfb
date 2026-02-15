import math

from pycfb.constants import *
from pycfb.context import CFBContext
from pycfb.enums import Sector

class CFBMinistreamMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        for idx, stream in enumerate(self.ctx.stream_data):
            if len(stream) < SIZE_MINISTREAM_CUTOFF_BYTES:
                self.ctx.ministream_start_minisectors[idx] = self.ctx.next_minifat
                self.write_stream(stream)

    def write_stream(self, stream_data: bytes):
        view = memoryview(self.ctx.minidata)
        stream_size_sectors = math.ceil(len(stream_data) / self.ctx.minisector_size_bytes)

        for x in range(stream_size_sectors):
            start = x * self.ctx.minisector_size_bytes
            chunk = stream_data[start : start + self.ctx.minisector_size_bytes]
            if len(chunk) < self.ctx.minisector_size_bytes: chunk = chunk.ljust(self.ctx.minisector_size_bytes, b'\x00')

            offset = self.ctx.next_minifat * self.ctx.minisector_size_bytes
            self.ctx.minifat_mgr.update(self.ctx.next_minifat, Sector.ENDOFCHAIN)
            if (x > 0): self.ctx.minifat_mgr.update(self.ctx.next_minifat - 1, self.ctx.next_minifat)
            view[offset : offset + self.ctx.minisector_size_bytes] = chunk
            self.ctx._increment_next_minifat()