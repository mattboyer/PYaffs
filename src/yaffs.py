#!/usr/bin/env python3

import sys
import os
import io
import argparse

import fs_entities
import block_entities


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
        return block_entities.Spare(data_bytes)

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
            if not (0xFFFF == spare.bytecount or spare.is_header):
                continue
            header_bytes = self.read_block_data(idx)
            header = block_entities.ObjectHeader(header_bytes, spare.objectid)
            self.headers[header.objectid] = header

    def read_block_data(self, block_idx):
        block_spare = self.spares[block_idx]
        if block_spare.is_header:
            num_bytes_to_read = 2048
        else:
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
    parser.add_argument(
        "action",
        choices=('list', 'ls', 'dump', 'extract', 'find')
    )
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
            if not args.output_path:
                args.output_path = args.fs_path.split(fs_entities.PATH_SEP)[-1]

            with open(args.output_path, 'wb') as outfile:
                outfile.write(file_object.read())
                outfile.close()
    return 0

if '__main__' == __name__:
    sys.exit(dispatcher())
