[![Build Status](https://travis-ci.org/mattboyer/PYaffs.svg?branch=master)](https://travis-ci.org/mattboyer/PYaffs)

# Hacklog

This tool is a by-product of a reverse-engineering project I'm blogging about at [Matt's Forensic Adventure](http://mattboyer.github.io/PYaffs/)

# PYaffs

This is a python library and CLI tool to access the YAFFS filesystem stored in a raw NAND flash dump taken from a [MediaTek](http://www.mediatek.com/)-based Android phone I own.

**Warning** This is highly experimental and the product of a reverse-engineering effort based on a single NAND dump. I don't expect this to work on any other dump, and neither should you.

## Using PYaffs

You don't want to.

OK, if you insist

```shell
$ src/pyaffs.py list <nand.img> [<path>]
$ src/pyaffs.py extract <nand.img> <path> <dest_path>
$ src/pyaffs.py find <nand.img> <name>
```

## Notes on the NAND layout

Right now, PYaffs hardcodes several important parameters regarding the layout of data in the NAND dump. These should be made parameterisable in future.

Here are the assumptions currently made:
- Each page comprises 2048 bytes of data
- Each page is interlaced with 4 16-byte segments of "spare" data, one every 512 bytes

Most information is taken from the official [YAFFS v1 spec](http://www.yaffs.net/yaffs-original-specification), although the spare layout is the product of ~~reverse-engineering~~ glorified guesswork.

Use at your own risk.
