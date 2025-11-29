import struct


class VLC:
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


def refill():
    nonlocal ptr, bits_dword, bits_left
    if ptr + 4 <= limit:
        bits_dword = struct.unpack_from("<I", data, ptr)[0]
        ptr += 4
        bits_left = 32
    else:
        bits_dword = 0
        bits_left = 0


def vlc_decompress(src_bytes):
    def read_u32(offset):
        return struct.unpack_from("<I", src_bytes, offset)[0]

    decompressed_size = read_u32(0x90) + 20000
    result = bytearray(decompressed_size)

    num_pieces = read_u32(0x28)
    num_pieces = 2 if num_pieces != 1 else 1

    width = read_u32(0x1C)
    var_30 = width // num_pieces
    var_2C = var_30

    ecx = read_u32(0)
    var_18 = var_2C // (2 if ecx != 0 else 1)
    var_10 = var_18

    data_ptr = src_bytes[0x9C:]
    small_table_size = read_u32(0x24)

    eax = var_18 * var_10
    ecx = var_30 * var_2C
    var_C = ecx + 2 * eax

    data_offset = 0
    big_index_count = struct.unpack_from("<I", data_ptr, data_offset)[0]
    data_offset += 4

    big_index_tab = list(
        struct.unpack_from(f"<{big_index_count}I", data_ptr, data_offset)
    )
    big_index_tab[0] = -0x80000000  # int.MinValue
    data_offset += big_index_count * 4

    used_bytes = VLC.gen_tabs(data_ptr, data_offset, big_index_tab, big_index_count)
    data_offset += used_bytes

    # Inlined fast decompression chunk
    def decompress_chunk_fast(data, data_offset, out_array, start_offset, data_size):
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
                idx = f2
                while idx >= 0:
                    b = get_bit()
                    if b == -1:
                        return
                    idx = VLC.Tab1[idx]["field_0"] if b else VLC.Tab1[idx]["field_1"]
                    idx -= VLC.SavedIndexCount
                value = VLC.SavedIndexTab[idx + VLC.SavedIndexCount]
                struct.pack_into("<I", out_array, index, value)
                index += 4
            elif f0 == float("-inf"):
                count = get_bits(f1 + 2)
                if count < 0:
                    return
                count = (count << (8 - f1)) | (code >> f1)
                out_array[index : index + count * 4] = b"\x00" * (count * 4)
                index += count * 4
            else:
                struct.pack_into("<I", out_array, index, f0)
                index += 4
                code >>= f1
                add = get_bits(f1)
                if add == -1:
                    return
                code |= add << (8 - f1)

            code = get_bits(8)

    # Loop over pieces
    for piece_num in range(read_u32(0x28)):
        table_size = small_table_size * small_table_size * 4
        offset_base = (var_C + 0x40) * piece_num * 4

        # Piece 1
        out_offset = offset_base
        result[out_offset : out_offset + table_size] = data_ptr[
            data_offset : data_offset + table_size
        ]
        data_offset += table_size

        size = read_u32(0x5C + piece_num * 4)
        decompress_chunk_fast(
            data_ptr, data_offset, result, out_offset + table_size, size
        )
        data_offset += size

        # Piece 2
        out_offset = offset_base + var_30 * var_2C * 4 + 0x80
        result[out_offset : out_offset + table_size] = data_ptr[
            data_offset : data_offset + table_size
        ]
        data_offset += table_size

        size = read_u32(0x6C + piece_num * 4)
        decompress_chunk_fast(
            data_ptr, data_offset, result, out_offset + table_size, size
        )
        data_offset += size

        # Piece 3
        out_offset = (
            offset_base + var_30 * var_2C * 4 + 0x80 + var_18 * var_10 * 4 + 0x80
        )
        result[out_offset : out_offset + table_size] = data_ptr[
            data_offset : data_offset + table_size
        ]
        data_offset += table_size

        size = read_u32(0x7C + piece_num * 4)
        decompress_chunk_fast(
            data_ptr, data_offset, result, out_offset + table_size, size
        )
        data_offset += size

    return result
