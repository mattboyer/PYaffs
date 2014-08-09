class Blob(object):

    def __init__(self, bytes):
        self._inner_bytes = bytes

    @staticmethod
    def bytes_to_binary(bytearray):
        bit_array = list()
        for byte in bytearray:
            bin_string = bin(byte)[2:]
            if 8 > len(bin_string):
                bin_string = ('0' * (8 - len(bin_string))) + bin_string
            bit_array.append(bin_string)

        bit_array = ''.join(bit_array)
        return bit_array

    def little_endian_bytes_to_int(self, offset, length):
        if 0 != length % 8:
            raise ValueError("length must be a multiple of 8")
        if length not in (8, 16, 24, 32):
            raise ValueError("Weird field length")

        byte_length = int(length / 8)
        field_bytes = self._inner_bytes[offset:offset + byte_length]

        int_value = int()
        for byte_idx, byte in enumerate(field_bytes):
            int_value += byte * (256 ** byte_idx)
        return int_value

    def bytes_to_string(self, offset, length):
        # length is in bytes
        string_value = ''.join(
            [chr(byte) for byte in self._inner_bytes[offset:length]]
        ).strip('\x00')
        return string_value


class Spare(Blob):
    def __init__(self, bytes):
        Blob.__init__(self, bytes)

        assert 64 == len(self._inner_bytes)
        self._inner_bits = Spare.bytes_to_binary(self._inner_bytes)
        assert 512 == len(self._inner_bits)
        self.objectid = self.little_endian_bits_to_int(40, 18)

        self.chunkid = self.little_endian_bytes_to_int(18, 16)
        self.is_header = (32768 == self.little_endian_bits_to_int(160, 16))

        self.bad_spare = False
        bytecount_low = self.little_endian_bits_to_int(176, 16)
        bytecount_high = self.little_endian_bits_to_int(264, 16)

        self.bytecount = bytecount_low + (2**16) * bytecount_high

    def little_endian_bits_to_int(self, bit_offset, length):

        bit_substring = self._inner_bits[bit_offset:bit_offset + length]

        bits_as_int = int()

        if 0 == length % 8:
            range_end = int(length / 8)
        else:
            range_end = 1 + int(length/8)

        for byte_idx in range(range_end):
            range_start = 8 * byte_idx
            range_end = min(8 * (1 + byte_idx), length)
            byte_as_int = int(bit_substring[range_start:range_end], 2)

            bits_as_int += byte_as_int * (256 ** byte_idx)

        return bits_as_int

    def __str__(self):
        return str(self._inner_bits)

    def __repr__(self):
        return "<Spare objectId:{0} chunkid:{1} bytecount:{2} header:{3}>".format(
            self.objectid,
            self.chunkid,
            self.bytecount,
            self.is_header,
        )


class ObjectHeader(Blob):
    header_types = {
        0: "UNKNOWN",
        1: "file",
        2: "symlink",
        3: "dir",
        4: "hardlink",
        5: "special",
    }

    def __init__(self, bytes, objectid):
        Blob.__init__(self, bytes)

        self.objectid = objectid

        self.object_type = self.little_endian_bytes_to_int(0, 32)
        self.parent_objid = self.little_endian_bytes_to_int(4, 32)
        self.name_chksum = self.little_endian_bytes_to_int(8, 16)
        self.name = self.bytes_to_string(10, 256)
        self.mode = self.little_endian_bytes_to_int(268, 32)
        self.uid = self.little_endian_bytes_to_int(272, 32)
        self.gid = self.little_endian_bytes_to_int(276, 32)
        self.atime = self.little_endian_bytes_to_int(280, 32)
        self.mtime = self.little_endian_bytes_to_int(284, 32)
        self.ctime = self.little_endian_bytes_to_int(288, 32)
        self.size = self.little_endian_bytes_to_int(292, 32)

    def __str__(self):
        return str(self._inner_bytes)

    def __repr__(self):
        return "<ObjectHeader: {i} {t} \"{name}\" parent {p} size {s}>".format(
            i=self.objectid,
            name=self.name,
            t=self.header_types[self.object_type],
            p=self.parent_objid,
            s=self.size,
        )
