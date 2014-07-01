#!/usr/bin/python

import sys
import os
import io

class Block(object):
    def __init__(self, bytes):
        self._inner_bytes = bytes
        self.object_type = self.little_endian_bytes_to_int(0, 32)
        self.parent_objId = self.little_endian_bytes_to_int(4, 32)
        self.name_chksum = self.little_endian_bytes_to_int(8, 16)
        self.name = self.bytes_to_string(10, 100)

    def __str__(self):
        return str(self._inner_bytes)

    def little_endian_bytes_to_int(self, offset, length):
        if 0 != length % 8:
            raise ValueError("length must be a multiple of 8")
        if length not in (8,16,32):
            raise ValueError("Weird field length")

        byte_length = int(length / 8)
        field_bytes = self._inner_bytes[offset:byte_length]

        int_value = int()
        for byte_idx, byte in enumerate(field_bytes):
            int_value += byte * (256 ** byte_idx)
        return int_value

    def bytes_to_string(self, offset, length):
        # length is in bytes
        string_value = ''.join([chr(byte) for byte in self._inner_bytes[offset:length]]).strip('\x00')
        return string_value

class Dumper(object):

    def __init__(self, file_stream):
        self._stream = file_stream
        self.spares = list()

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

    @staticmethod
    def object_id_from_spare(bit_array):
        assert 128 == len(bit_array), len(bit_array)

        object_id = bit_array[40:58]

        first_byte_as_int = int(object_id[:8], 2)
        second_byte_as_int = int(object_id[8:16], 2)
        runt_as_int = int(object_id[16:], 2)

        object_id_as_int = 1024 * runt_as_int + 256 * second_byte_as_int + first_byte_as_int

        return object_id_as_int

    def read_block_data(self, block_idx):
        self._stream.seek(528 * block_idx, io.SEEK_SET)
        data_bytes = self._stream.read(512)
        if 512 != len(data_bytes):
            raise IOError("Couldn't read block {0}".format(block_idx))
        return Block(data_bytes)

    def find(self, file_name):

        matches = list()
        for idx, spare in enumerate(self.spares):
            block = self.read_block_data(idx)
            if file_name == block.name:
                matches.append((idx, block, spare))
            else:
                del block

        return matches

    def find_blocks_for_objid(self, objid):
        matches = list()
        for idx, spare in enumerate(self.spares):
            spare_objid = self.object_id_from_spare(self.bytes_to_binary(spare))
            if objid == spare_objid:
                matches.append((idx, self.read_block_data(idx)))
        return matches

    def read_spare_data(self):
        while True:
            self._stream.seek(512, io.SEEK_CUR)
            spare_bytes = self._stream.read(16)
            if len(spare_bytes):
                self.spares.append(spare_bytes)
            else:
                return

def spike():
    # TODO Use argparse instead
    assert 2 == len(sys.argv)

    file_path = sys.argv[1]

    assert os.path.isfile(file_path)

    with open(file_path, 'rb') as yaffs_file:
        dumper = Dumper(yaffs_file)
        dumper.read_spare_data()

        print("{0} spares".format(len(dumper.spares)))
        matches = dumper.find("wpa_supplicant.conf")
        assert 1 == len(matches)
        header_idx, header_block, header_spare = matches[0]

        spare_as_binary = dumper.bytes_to_binary(header_spare)
        objectid = dumper.object_id_from_spare(spare_as_binary)
        print("objectId for file is {0}".format(objectid))

        matches = dumper.find_blocks_for_objid(objectid)
        print(len(matches))
        for (idx, match) in matches:
            print(str(match))
            print(dumper.bytes_to_binary(dumper.spares[idx]))


        # TODO Figure out the length of wpa_supplicant.conf from the header and
        # cross-ref that to the 16 bytes of spare

        #for idx, spare in enumerate(dumper.spares):
            #tentative_block = dumper.read_block_data(idx)
            #if 1 != tentative_block.object_type:
                #del tentative_block
                #continue
            #if 20 > len(tentative_block.name):
                #print(tentative_block.name)


if '__main__' == __name__:
    spike()
