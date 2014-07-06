#!/usr/bin/env python3

import sys
import os
import io
import argparse

import fs_entities

# I should probably split these into another module


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
        if length not in (8,16,24,32):
            raise ValueError("Weird field length")

        byte_length = int(length / 8)
        field_bytes = self._inner_bytes[offset:offset + byte_length]

        int_value = int()
        for byte_idx, byte in enumerate(field_bytes):
            int_value += byte * (256 ** byte_idx)
        return int_value

    def bytes_to_string(self, offset, length):
        # length is in bytes
        string_value = ''.join([chr(byte) for byte in self._inner_bytes[offset:length]]).strip('\x00')
        return string_value

class Spare(Blob):
    def __init__(self, bytes):
        Blob.__init__(self, bytes)

        assert 64 == len(self._inner_bytes)
        self._inner_bits = Spare.bytes_to_binary(self._inner_bytes)
        assert 512 == len(self._inner_bits)
        self.objectid = self.little_endian_bits_to_int(40, 18)

        self.chunkid = self.little_endian_bytes_to_int(18, 16)

        self.bad_spare = False
        self.bytecount = self.little_endian_bits_to_int(176, 16)

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
        return "<spare objectId:{0} chunkid:{1} bytecount:{2} bad:{3}>".format(self.objectid, self.chunkid, self.bytecount, self.bad_spare)

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

class Dumper(object):

    def __init__(self, file_stream):
        self._stream = file_stream
        self.spares = list()
        self.headers = dict()

    def read_spare_data(self, block_idx):
        # We'll read the 2048 bytes of data of index block_idx
        self._stream.seek(2112 * block_idx, io.SEEK_SET)
        data_bytes = bytes()

        # Read four times
        for quartet_idx in range(4):
            self._stream.seek(512, io.SEEK_CUR)

            read_bytes = self._stream.read(16)
            if 16 != len(read_bytes):
                raise IOError("Couldn't read spare {0}".format(block_idx))
            data_bytes += read_bytes
        assert 64 == len(data_bytes)
        return Spare(data_bytes)

    def read_all_spares(self):
        idx = 0
        while True:
            try:
                self.spares.append(self.read_spare_data(idx))
                idx += 1
            except IOError:
                break
        return idx

    def read_headers(self):
        for idx, spare in enumerate(self.spares):
            if not (0 == spare.chunkid and 0xFFFF == spare.bytecount):
                continue
            header_bytes = self.read_block_data(idx)
            header = ObjectHeader(header_bytes, spare.objectid)
            self.headers[header.objectid] = header

    def read_block_data(self, block_idx):
        num_bytes_to_read = self.spares[block_idx].bytecount

        # We'll read the 2048 bytes of data of index block_idx
        self._stream.seek(2112 * block_idx, io.SEEK_SET)
        data_bytes = bytes()

        # Read four times
        for quartet_idx in range(4):
            read_bytes = self._stream.read(512)
            if 512 != len(read_bytes):
                raise IOError("Couldn't read block {0}".format(block_idx))
            data_bytes += read_bytes

            self._stream.seek(16, io.SEEK_CUR)

        data_bytes = data_bytes[:num_bytes_to_read]
        # We should return straight bytes to be passed to ObjectHeader at the
        # caller's discretion
        return data_bytes


def dispatcher():
    parser = argparse.ArgumentParser(description="GRUH")
    parser.add_argument("action", choices=('list', 'ls', 'dump', 'extract', 'find'))
    parser.add_argument("YAFFS_file")
    parser.add_argument("fs_path", nargs="?")
    parser.add_argument("output_path", nargs="?")

    args = parser.parse_args()

    assert os.path.isfile(args.YAFFS_file)

    with open(args.YAFFS_file, 'rb') as yaffs_file:
        dumper = Dumper(yaffs_file)

        num_blocks = dumper.read_all_spares()
        print("{0} blocks".format(num_blocks))
        dumper.read_headers()

        fs = fs_entities.FileSystem(dumper)
        if args.action in ('ls', 'list'):
            if not args.fs_path:
                fs.root_object.walk()
            else:
                fs_object = fs.get_obj_from_path(args.fs_path)
                if isinstance(fs_object, fs_entities.FSDir):
                    fs_object.walk()
                else:
                    print(fs_object)

        elif 'find' == args.action:
            results = fs.find(fs_entities.FSFile, 'netdiag')
            print(results)
        elif 'extract' == args.action:
            assert args.fs_path
            file_object = fs.get_obj_from_path(args.fs_path)
            if not isinstance(file_object, fs_entities.FSFile):
                raise IOError("Cannot extract {0}".format(repr(file_object)))
            if args.output_path:
                with open(args.output_path, 'wb') as outfile:
                    outfile.write(file_object.read())
                    outfile.close()
            else:
                sys.stdout.write(file_object.read().decode("utf-8"))

    return 0

if '__main__' == __name__:
    sys.exit(dispatcher())
