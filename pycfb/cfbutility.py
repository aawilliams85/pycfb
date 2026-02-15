import uuid

from pycfb.context import CFBContext
from pycfb.difat import CFBDifatMgr
from pycfb.directory import CFBDirectoryMgr
from pycfb.fat import CFBFatMgr
from pycfb.header import CFBHeaderMgr
from pycfb.minifat import CFBMinifatMgr
from pycfb.ministream import CFBMinistreamMgr
from pycfb.stream import CFBStreamMgr

class CFBWriter:
    def __init__(
        self,
        stream_names: list[str],
        stream_paths: list[str],
        stream_data: list[bytes],
        root_clsid: uuid.UUID
    ):
        self.ctx = CFBContext(stream_names, stream_paths, stream_data, root_clsid)
        self.ctx.header_mgr = CFBHeaderMgr(self.ctx)
        self.ctx.fat_mgr = CFBFatMgr(self.ctx)
        self.ctx.minifat_mgr = CFBMinifatMgr(self.ctx)
        self.ctx.difat_mgr = CFBDifatMgr(self.ctx)
        self.ctx.ministream_mgr = CFBMinistreamMgr(self.ctx)
        self.ctx.stream_mgr = CFBStreamMgr(self.ctx)
        self.ctx.directory_mgr = CFBDirectoryMgr(self.ctx)

        self.ctx.data = bytearray(self.ctx._calc_total_size_bytes())
        self.ctx.ministream_data = bytearray(self.ctx._calc_ministream_size_bytes())

        self.ctx.header_mgr.allocate()
        self.ctx.fat_mgr.allocate()
        self.ctx.minifat_mgr.allocate()
        self.ctx.difat_mgr.allocate()
        self.ctx.ministream_mgr.allocate()
        self.ctx.stream_mgr.allocate()
        self.ctx.directory_mgr.allocate()
        self.ctx.header_mgr.update()

    @property
    def data(self):
        return self.ctx.data