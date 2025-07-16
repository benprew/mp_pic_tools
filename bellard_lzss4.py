import struct

"""
Pic98 files are compressed using Bellar's lzss algorithm. This is based off of the
lzexe reproduction https://github.com/mywave82/unlzexe.

See: https://canadianavenger.io/2024/06/26/oops-i-did-it-again/ for details of the
format
"""


class BitStream:
    def __init__(self, file):
        self.fp = file
        self.count = 0x10
        buf = self.fp.read(2)
        if len(buf) < 2:
            raise EOFError("Unexpected EOF while initializing bit buffer")
        self.buf = struct.unpack("<H", buf)[0]

    def getbit(self):
        b = self.buf & 1
        self.count -= 1
        if self.count == 0:
            buf = self.fp.read(2)
            if len(buf) < 2:
                raise EOFError("Unexpected EOF while reloading bit buffer")
            self.buf = struct.unpack("<H", buf)[0]
            self.count = 0x10
        else:
            self.buf >>= 1
        return b


def lzss_decompress(ifile, start_offset=0):
    # Seek to compressed data start
    ifile.seek(start_offset)
    bits = BitStream(ifile)
    data = bytearray(0x4500)
    p = 0
    out = bytearray()

    while True:
        if p > 0x4000:
            out.extend(data[:0x2000])
            data[:0x2500] = data[0x2000:p] + bytearray(0x500)  # Slide
            p -= 0x2000

        if bits.getbit():
            b = ifile.read(1)
            if not b:
                break
            data[p] = b[0]
            p += 1
            continue

        if not bits.getbit():
            len_ = (bits.getbit() << 1) | bits.getbit()
            len_ += 2
            b = ifile.read(1)
            if not b:
                break
            span = b[0] | 0xFF00
        else:
            b1 = ifile.read(1)
            b2 = ifile.read(1)
            if not b1 or not b2:
                break
            span = b1[0]
            len_ = b2[0]
            span |= ((len_ & ~0x07) << 5) | 0xE000
            len_ = (len_ & 0x07) + 2
            if len_ == 2:
                b = ifile.read(1)
                if not b:
                    break
                len_ = b[0]
                if len_ == 0:
                    break  # End of stream
                elif len_ == 1:
                    continue  # Segment change, ignore
                else:
                    len_ += 1

        for _ in range(len_):
            ref = p + int(struct.unpack("<h", struct.pack("<H", span))[0])
            data[p] = data[ref]
            p += 1

    out.extend(data[:p])
    return out
