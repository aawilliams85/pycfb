import math

from pycfb.constants import *
from pycfb.context import CFBContext
from pycfb.enums import Sector

class CFBStreamMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        for idx, stream in enumerate(self.ctx.stream_data):
            if len(stream) >= SIZE_MINISTREAM_CUTOFF_BYTES:
                self.ctx.stream_start_sectors[idx] = self.ctx.next_freesect_number
                self.write_stream(stream)
        if (len(self.ctx.minidata) > 0):
            self.ctx.ministream_start = self.ctx.next_freesect_number
            self.ctx.stream_start_sectors.append(self.ctx.next_freesect_number)
            self.write_stream(bytes(self.ctx.minidata))

    def write_stream(self, stream_data: bytes):
        view = memoryview(self.ctx.data)
        stream_size_sectors = math.ceil(len(stream_data) / self.ctx.sector_size_bytes)
        
        for x in range(stream_size_sectors):
            start = x * self.ctx.sector_size_bytes
            chunk = stream_data[start : start + self.ctx.sector_size_bytes]            
            if len(chunk) < self.ctx.sector_size_bytes: chunk = chunk.ljust(self.ctx.sector_size_bytes, b'\x00')

            offset = self.ctx.next_freesect_offset
            sector = offset // self.ctx.sector_size_bytes
            if (x > 0): self.ctx.fat_mgr.update(self.ctx.next_fat - 1, self.ctx.next_fat)
            self.ctx.fat_mgr.update(self.ctx.next_fat, Sector.ENDOFCHAIN)
            view[offset : offset + self.ctx.sector_size_bytes] = chunk
            self.ctx._increment_next_fat()
            self.ctx._increment_next_freesect()
