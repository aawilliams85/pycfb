# pycfb
PyCFB (Python Compound File Binary Utility) is a naive implementation of Microsoft's Compound File Binary (CFB) format.  

Limitations include:
- Only supports v3.0 of the specification (512-byte sectors).
- Only supports CFB writing (not reading), and only in one shot (all files sequentially written to a new file).
- Red/black tree not implemented correctly.