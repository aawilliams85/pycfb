from pycfb.constants import HEADER_DIFAT_COUNT
from pycfb.context import CFBContext
from pycfb.enums import Sector
from pycfb.types import DifatSector

class CFBDifatMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        for x in range(self.ctx.calc_difat_size_sectors()):
            # Initialize the next DIFAT sector
            new_sector = DifatSector.from_buffer(self.ctx.data, self.ctx.next_freesect_offset)
            for y in range(self.ctx.difat_entries_per_sector):
                new_sector.entries[y] = Sector.FREESECT
            new_sector.next_difat = Sector.ENDOFCHAIN

            # Chain the previous DIFAT sector to this one
            if x > 0:
                self.ctx.difat[x-1].next_difat = self.ctx.get_sector_number(new_sector)

            # Add it to the DIFAT list and update FAT to mark this sector as DIFSECT
            self.ctx.difat.append(new_sector)
            self.ctx.fat_mgr.update(self.ctx.get_sector_number(new_sector), Sector.DIFSECT)
            self.ctx.inc_next_fat()
            self.ctx.inc_next_freesect()

        for x, fat_entry in enumerate(self.ctx.fat):
            self.update(x, self.ctx.get_sector_number(fat_entry))

        header_excess = HEADER_DIFAT_COUNT - len(self.ctx.fat)
        if header_excess > 0:
            for x in range(header_excess):
                self.update(len(self.ctx.fat) + x, Sector.FREESECT)

    def update(self, index: int, value: int):
        if index < HEADER_DIFAT_COUNT:
            self.ctx.header.sector_data_difat[index] = value
        else:
            index_remainder = index - HEADER_DIFAT_COUNT
            sector_idx = index_remainder // self.ctx.difat_entries_per_sector
            entry_idx = index_remainder % self.ctx.difat_entries_per_sector
            self.ctx.difat[sector_idx].entries[entry_idx] = value
