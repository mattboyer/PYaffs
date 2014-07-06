#PYaffs

This is a python library and CLI tool to access the YAFFS filesystem stored in a raw NAND flash dump taken from a MTK-based Android phone I own

**Warning** This is highly experimental and the product of a reverse-engineering effort based on a single NAND dump. I don't expect this to work on any other dump, and neither should you.

##Using PYaffs

You don't want to.

OK, if you insist

```shell
$ src/pyaffs.py list <nand.img> [<path>]
$ src/pyaffs.py extract <nand.img> <path> <dest_path>
```

##Notes on the NAND layout

Right now, PYaffs hardcodes several important parameters regarding the layout of data in the NAND dump. These should be made parameterisable in future.

Here are the assumptions currently made:
- Page size is 2048 bytes
- Each page is interlaced with 4 16-bytes segments of "spare" data, one every 512 bytes

As previously mentioned, these parameters are the product of ~~reverse-engineering~~ glorified guesswork.

Use at your own risk.

##And now for something completely different

[Matt's Forensic Adventure](http://mattboyer.github.io/PYaffs/)
