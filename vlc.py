import struct


class VLC:
    debug = False

    bits_left = 0
    bitstream = b""
    bitstream_start = 0
    bitstream_ptr = 0
    bitstream_limit = 0
    bits_dword = 0
    bits_dword_mask = [0xFFFFFFFF >> i for i in range(32)]

    Tab1 = []
    Tab2 = [{"field_0": 0, "field_1": 0, "field_2": 0} for _ in range(256)]

    SavedIndexCount = 0
    SavedIndexTab = []

    @staticmethod
    def get_bits(bits):
        if bits <= VLC.bits_left:
            value = VLC.bits_dword & VLC.bits_dword_mask[32 - bits]
            VLC.bits_dword >>= bits
            VLC.bits_left -= bits
            return value
        else:
            value = VLC.bits_dword
            bits -= VLC.bits_left
            if VLC.bitstream_ptr - VLC.bitstream_start + 4 < VLC.bitstream_limit:
                VLC.bits_dword = struct.unpack_from(
                    "<I", VLC.bitstream, VLC.bitstream_ptr
                )[0]
                VLC.bitstream_ptr += 4
                value |= (
                    VLC.bits_dword & VLC.bits_dword_mask[32 - bits]
                ) << VLC.bits_left
                VLC.bits_dword >>= bits
                VLC.bits_left = 32 - bits
                return value
            else:
                return -1

    @staticmethod
    def get_next_bit():
        if VLC.bits_left == 0:
            bytes_left = VLC.bitstream_limit - (VLC.bitstream_ptr - VLC.bitstream_start)
            if bytes_left <= 0:
                return -1
            if bytes_left < 4:
                VLC.bits_dword = sum(
                    (VLC.bitstream[VLC.bitstream_ptr + i] << (8 * i))
                    for i in range(bytes_left)
                )
                VLC.bitstream_ptr += bytes_left
            else:
                VLC.bits_dword = struct.unpack_from(
                    "<I", VLC.bitstream, VLC.bitstream_ptr
                )[0]
                VLC.bitstream_ptr += 4
            VLC.bits_left = 32

        bit_out = VLC.bits_dword & 1
        VLC.bits_dword >>= 1
        VLC.bits_left -= 1
        return bit_out

    @staticmethod
    def gen_tab2(count):
        stack = []
        path_bits = [1] * 32
        current = count - 1
        stack.append(current)
        level = 0

        while path_bits[0] >= 0:
            if path_bits[level] != 0:
                current = VLC.Tab1[current]["field_0"]
            else:
                current = VLC.Tab1[current]["field_1"]

            next_index = current - VLC.SavedIndexCount
            stack.append(next_index)
            level += 1

            if next_index >= 0:
                if level == 8:
                    val = sum(path_bits[i] << i for i in range(level))
                    VLC.Tab2[val] = {
                        "field_0": float("inf"),
                        "field_1": level,
                        "field_2": next_index,
                    }
                    path_bits[level] = 1
                    level -= 1
                    path_bits[level] -= 1
                    current = stack[level]
                continue

            val = sum(path_bits[i] << i for i in range(level))
            for i in range(1 << (8 - level)):
                idx = (i << level) | val
                VLC.Tab2[idx] = {
                    "field_0": VLC.SavedIndexTab[current],
                    "field_1": level,
                    "field_2": -1,
                }

            path_bits[level] = 1
            level -= 1
            path_bits[level] -= 1
            current = stack[level]

            while path_bits[0] >= 0 and path_bits[level] < 0:
                path_bits[level] = 1
                level -= 1
                path_bits[level] -= 1
                current = stack[level]

    @staticmethod
    def gen_tabs(data, offset, index_tab, index_count):
        VLC.bitstream = data
        VLC.bitstream_start = VLC.bitstream_ptr = offset
        VLC.bitstream_limit = len(data) - offset
        VLC.bits_dword = 0
        VLC.bits_left = 0

        tab1_count = VLC.get_bits(13)
        VLC.Tab1 = [
            {"field_0": VLC.get_bits(13), "field_1": VLC.get_bits(13)}
            for _ in range(tab1_count)
        ]

        VLC.SavedIndexCount = index_count
        VLC.SavedIndexTab = index_tab
        VLC.gen_tab2(tab1_count)

        return (13 + 26 * tab1_count + 7) // 8

    @staticmethod
    def decompress_chunk(data, data_offset, out_array, start_offset, data_size):
        index = start_offset
        VLC.bitstream = data
        VLC.bitstream_ptr = data_offset
        VLC.bitstream_start = data_offset
        VLC.bitstream_limit = data_size

        if data_offset & 3:
            unaligned_bytes = 4 - (data_offset & 3)
            VLC.bits_left = unaligned_bytes * 8
            mask = 0xFFFFFFFF >> (32 - VLC.bits_left)
            VLC.bits_dword = struct.unpack_from("<I", data, data_offset)[0] & mask
            VLC.bitstream_ptr += unaligned_bytes
        else:
            VLC.bits_left = 0
            VLC.bits_dword = 0

        code = VLC.get_bits(8)

        while code != -1:
            entry = VLC.Tab2[code]
            if entry["field_0"] == float("inf"):
                idx = entry["field_2"]
                while idx >= 0:
                    bit = VLC.get_next_bit()
                    if bit == -1:
                        return
                    idx = VLC.Tab1[idx]["field_0"] if bit else VLC.Tab1[idx]["field_1"]
                    idx -= VLC.SavedIndexCount
                value = VLC.SavedIndexTab[idx + VLC.SavedIndexCount]
                out_array[index : index + 4] = struct.pack("<I", value)
                index += 4
            elif entry["field_0"] == float("-inf"):
                count = VLC.get_bits(entry["field_1"] + 2)
                if count < 0:
                    break
                count = (count << (8 - entry["field_1"])) | (code >> entry["field_1"])
                out_array[index : index + count * 4] = b"\x00" * (count * 4)
                index += count * 4
            else:
                out_array[index : index + 4] = struct.pack("<I", entry["field_0"])
                index += 4
                code >>= entry["field_1"]
                next_bits = VLC.get_bits(entry["field_1"])
                if next_bits == -1:
                    break
                code |= next_bits << (8 - entry["field_1"])

            code = VLC.get_bits(8)


class VLCFast:
    def decompress_chunk(data, data_offset, out_array, start_offset, data_size):
        index = start_offset
        ptr = data_offset
        limit = data_offset + data_size
        bits_left = 0
        bits_dword = 0

        def refill():
            nonlocal ptr, bits_dword, bits_left
            if ptr + 4 <= limit:
                bits_dword = struct.unpack_from("<I", data, ptr)[0]
                ptr += 4
                bits_left = 32
            else:
                bits_dword = 0
                bits_left = 0

        def get_bits(n):
            nonlocal bits_dword, bits_left, ptr
            if bits_left >= n:
                val = bits_dword & ((1 << n) - 1)
                bits_dword >>= n
                bits_left -= n
                return val
            elif ptr + 4 <= limit:
                val = bits_dword
                needed = n - bits_left
                bits_dword = struct.unpack_from("<I", data, ptr)[0]
                ptr += 4
                val |= (bits_dword & ((1 << needed) - 1)) << bits_left
                bits_dword >>= needed
                bits_left = 32 - needed
                return val
            else:
                return -1

        def get_bit():
            nonlocal bits_dword, bits_left, ptr
            if bits_left == 0:
                refill()
                if bits_left == 0:
                    return -1
                bit = bits_dword & 1
                bits_dword >>= 1
                bits_left -= 1
            return bit

        code = get_bits(8)

        while code != -1:
            entry = VLC.Tab2[code]
            f0 = entry["field_0"]
            f1 = entry["field_1"]
            f2 = entry["field_2"]

            if f0 == float("inf"):
                # Tree walk
                idx = f2
                while idx >= 0:
                    b = get_bit()
                    if b == -1:
                        return
                    idx = VLC.Tab1[idx]["field_0"] if b else VLC.Tab1[idx]["field_1"]
                    idx -= VLC.SavedIndexCount

                value = VLC.SavedIndexTab[idx + VLC.SavedIndexCount]
                out_array[index : index + 4] = struct.pack("<I", value)
                index += 4
            elif f0 == float("-inf"):
                # Zero block
                count = get_bits(f1 + 2)
                if count < 0:
                    return
                count = (count << (8 - f1)) | (code >> f1)
                end = index + count * 4
                out_array[index:end] = b"\x00" * (count * 4)
                index = end
            else:
                # Direct value
                out_array[index : index + 4] = struct.pack("<I", f0)
                index += 4
                code >>= f1
                add = get_bits(f1)
                if add == -1:
                    return
                code |= add << (8 - f1)

            code = get_bits(8)
