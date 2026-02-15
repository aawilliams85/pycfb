from pycfb.context import CFBContext
from pycfb.enums import Sector
from pycfb.types import FatSector

class CFBFatMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        for x in range(self.ctx.calc_fat_size_sectors()):
            new_sector = FatSector.from_buffer(self.ctx.data, self.ctx.next_freesect_offset)
            for y in range(self.ctx.fat_entries_per_sector):
                new_sector.entries[y] = Sector.FREESECT
            self.ctx.fat.append(new_sector)
            self.update(x,Sector.FATSECT)
            self.ctx.inc_next_fat()
            self.ctx.inc_next_freesect()

    def update(self, index: int, value: int):
        sector_idx = index // self.ctx.fat_entries_per_sector
        entry_idx = index % self.ctx.fat_entries_per_sector
        self.ctx.fat[sector_idx].entries[entry_idx] = value
