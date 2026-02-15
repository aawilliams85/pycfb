import ctypes

from pycfb.constants import *
from pycfb.context import CFBContext
from pycfb.enums import Sector
from pycfb.types import Header

class CFBHeaderMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        self.ctx.header = Header.from_buffer(self.ctx.data, self.ctx.next_freesect_offset)
        self.ctx._increment_next_freesect()

    def update(self):
        self.ctx.header.signature = HEADER_SIGNATURE
        self.ctx.header.version_minor = HEADER_VERSION_MINOR
        self.ctx.header.version_major = HEADER_VERSION_MAJOR
        self.ctx.header.byte_order = HEADER_BYTE_ORDER
        self.ctx.header.sector_shift = SHIFT_SECTOR_BITS_V3
        self.ctx.header.mini_sector_shift = SHIFT_MINISECTOR_BITS
        self.ctx.header.sector_count_directory = 0 # Always zero for v3
        self.ctx.header.sector_count_fat = len(self.ctx.fat)
        self.ctx.header.sector_start_directory = self.ctx._get_sector_number(self.ctx.directory[0])
        self.ctx.header.transaction_signature = 0
        self.ctx.header.mini_cutoff_size = SIZE_MINISTREAM_CUTOFF_BYTES

        if len(self.ctx.minifat) > 0:
            self.ctx.header.sector_start_minifat = self.ctx._get_sector_number(self.ctx.minifat[0])
            self.ctx.header.sector_count_minifat = len(self.ctx.minifat)
        else:
            self.ctx.header.sector_start_minifat = Sector.ENDOFCHAIN
            self.ctx.header.sector_count_minifat = 0

        if len(self.ctx.difat) > 0:
            self.ctx.header.sector_start_difat = self.ctx._get_sector_number(self.ctx.difat[0])
            self.ctx.header.sector_count_difat = len(self.ctx.difat)
        else:
            self.ctx.header.sector_start_difat = Sector.ENDOFCHAIN
            self.ctx.header.sector_count_difat = 0