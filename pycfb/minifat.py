from pycfb.context import CFBContext
from pycfb.enums import Sector
from pycfb.types import FatSector

class CFBMinifatMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        for x in range(self.ctx._calc_size_minifat_sectors()):
            new_sector = FatSector.from_buffer(self.ctx.data, self.ctx.next_freesect_offset)
            for y in range(self.ctx.fat_entries_per_sector): new_sector.entries[y] = Sector.FREESECT
            self.ctx.minifat.append(new_sector)
            self.ctx.fat_mgr.update(self.ctx.next_fat, Sector.ENDOFCHAIN)

            # Chain the previous MINIFAT sector to this one
            if (x > 0): self.ctx.fat_mgr.update(self.ctx.next_fat - 1, self.ctx._get_sector_number(new_sector))
            
            self.ctx._increment_next_fat()
            self.ctx._increment_next_freesect()

    def update(self, index: int, value: int):
        sector_idx = index // self.ctx.fat_entries_per_sector
        entry_idx = index % self.ctx.fat_entries_per_sector
        self.ctx.minifat[sector_idx].entries[entry_idx] = value
