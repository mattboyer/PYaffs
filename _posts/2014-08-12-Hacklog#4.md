---
layout: post
title: "Hacklog #4: Dump format and YAFFS"
tags: yaffs spare nand python filesystem
---

# Leitmotif

Well over twenty years ago, the movie [Jurassic Park](http://www.imdb.com/title/tt0107290/) came out. I remember there was a lot of exposition in the first act. In particular, there's a scene where a small group of people is given access -for the first time!- to an area of the island where very large dinosaurs roam free.

Among them is a man who is some sort of scientist and definitely not a people person. They happen upon a dino-sized *dump* of dino poo and yer man deadpans:

> That is one big pile of shit.

!["That is one big pile of shit"]({{ site.baseurl }}/images/BPOS.jpg)

He's not alone, of course. Accompanying him on the tour is Dr Sattler, a paleobotanist. Dr Sattler takes a keen interest in how plant life has been recreated in the park and seizes the opportunity to *explore the dump*:

!["Reverse-engineering"]({{ site.baseurl }}/images/reverse_engineering.jpg)

That scene, and this picture in particular, summarises this whole post.

Reverse engineering is a dirty job but someone's gotta do it.

# The Madcap YAFFS

So I [finally]({{site.baseurl}}{% post_url 2014-07-31-Hacklog#3 %}) have a raw Flash ROM dump of the partition on which my phone's `/system` filesystem [lives]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %}). I'm no longer constrained by file permissions - everything on that filesystem I now have access to.

I only need to figure out how.

## Context

As I saw in the output of [`mount(8)`](http://linux.die.net/man/8/mount), `/system` is a `yaffs2` filesystem, mounted read-only:

	$ mount
	
	/dev/block/mtdblock11 /system yaffs2 ro,noatime 0 0

[`YAFFS2`](http://www.yaffs.net/yaffs-2-specification) is the second revision of [`YAFFS`](http://www.yaffs.net/yaffs-original-specification), a Flash-optimised filesystem that's been around a while.

My first idea was to open the `/system` dump with a YAFFS access tool. None of them worked with the dumps I got out of my phone and this little project lost momentum and got stalled there for almost three months.

I eventually picked it up again and decided to do this the hard way. In order to access the filesystem's contents out-of-band, I had to spend time reading and digesting both filesystems' specification documents. The YAFFS2 spec is not a standalone document so familiarity with YAFFS stuff is pretty much required.

## A YAFFS primer

The basic unit of data storage in YAFFS is a **chunk**. A chunk may contain *either* filesystem stuff of the kind displayed by [`stat(1)`](http://linux.die.net/man/1/stat) (viz. inodes, file names, permissions, etc.) *or* file data.

Within the scope of the YAFFS documentation, filesystem entities such as files and directories are called **objects**. Every object has its metadata stored in a dedicated chunk in a data structure the YAFFS documentation calls an **object header**

The format for object headers is defined in [`yaffs_guts.h`](http://www.aleph1.co.uk/gitweb?p=yaffs2.git;a=blob;f=yaffs_guts.h;h=231f8ac567eb86e3583f4c1fc436e9c89a4ca2c8;hb=HEAD#l312) in the form of this plain old C struct:

{% highlight c %}
struct yaffs_obj_hdr {
        enum yaffs_obj_type type;

        /* Apply to everything  */
        int parent_obj_id;
        u16 sum_no_longer_used; /* checksum of name. No longer used */
        YCHAR name[YAFFS_MAX_NAME_LENGTH + 1];

        /* The following apply to all object types except for hard links */
        u32 yst_mode;           /* protection */

        u32 yst_uid;
        u32 yst_gid;
        u32 yst_atime;
        u32 yst_mtime;
        u32 yst_ctime;

        /* File size  applies to files only */
        u32 file_size_low;

        /* Equivalent object id applies to hard links only. */
        int equiv_id;

        /* Alias is for symlinks only. */
        YCHAR alias[YAFFS_MAX_ALIAS_LENGTH + 1];

        u32 yst_rdev;   /* stuff for block and char devices (major/min) */

        u32 win_ctime[2];
        u32 win_atime[2];
        u32 win_mtime[2];

        u32 inband_shadowed_obj_id;
        u32 inband_is_shrink;

        u32 file_size_high;
        u32 reserved[1];
        int shadows_obj;        /* This object header shadows the
                                specified object if > 0 */

        /* is_shrink applies to object headers written when wemake a hole. */
        u32 is_shrink;

};
{% endhighlight %}

As the YAFFS documentation points out, this is not just an in-memory structure, but also the format in which header information is stored on the NAND (ie. on the raw MTD). This was my starting point.

A given file may be split across several data chunks, independently of its header chunk. Since the object header format doesn't have any references to other chunks, it follows that some sort of metadata is needed *around* data chunks for the filesystem implementation to know what file a given chunk belongs to, and where that chunk falls in the ordered list of data chunks that comprise the whole file.

This data is stored in what the YAFFS docs call **spare** data. The docs mention that spare data is interleaved with "actual" chunk data but doesn't say much more beyond that.

The YAFFS2 document on the author's website is very vague when it comes to the format of spare data. In the original YAFFS docs, spare data is said to have a fixed sized of 16 bytes per chunk, each comprised of 8 bytes of a packed data structure referred to as of **tags**, 6 bytes of [ECC](http://en.wikipedia.org/wiki/ECC_memory) redundancy bits for for the chunk, a 1-byte block damaged chunk flag and an unused 16th byte.

The **tags** [data structure](http://www.aleph1.co.uk/gitweb?p=yaffs2.git;a=blob;f=yaffs_guts.h;hb=7e5cf0fa1b694f835cdc184a8395b229fa29f9ae#l146) is as follows:

{% highlight c %}
struct yaffs_tags {
        u32 chunk_id:20;
        u32 serial_number:2;
        u32 n_bytes_lsb:10;
        u32 obj_id:18;
        u32 ecc:12;
        u32 n_bytes_msb:2;
};
{% endhighlight %}

Let's see what we have here:

- `obj_id` - That's the object identifier - this lets us know which filesystem "entity" a given chunk belongs to. I think of that numeric identifier as an [*inode number*](http://www.linfo.org/inode.html).

- `chunk_id` - This is effectively the chunk's position in the ordered list of chunks that, together, hold the file's contents.

- `n_bytes_lsb` and `n_bytes_msb` - Together, these tell us how many bytes of *actual file data* are in the chunk. Unless a file's size happens to be a whole multiple of the chunk size, we'll need to know where to cut off the runt chunk.

- `ecc` - Just some extra redundancy bits derived from the tags themselves. This isn't very interesting to me.

- `serial_number` - Who knows?

Interestingly, the number of bytes in a chunk is stored on 10 + 2 bits, meaning that there can be up to 4095.

# Exploring the dump

I now have some idea of what I can expect to find in the dump. As I mentioned in the [first post]({{ site.baseurl }}{% post_url 2014-07-15-Hacklog#0 %}), I am particularly interested in a file named `/system/xbin/tcpdump`. I can expect to find a YAFFS object header for this file as well as for its parent dir `xbin`.

## Object Headers

Let's get greppin', yo!

	647-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ for offset in $(grep -abo tcpdump ../images/system.img  | cut -d':' -f1); do xxd -g4 -s ${offset} -l 16 ../images/system.img; done
	510782b: 74637064 756d7000 0c0c7463 7064756d  tcpdump...tcpdum
	5107835: 74637064 756d7020 73746f70 000a0a70  tcpdump stop...p
	5107a9b: 74637064 756d7000 0b0b7463 7064756d  tcpdump...tcpdum
	5107aa5: 74637064 756d705f 656e6400 0a0a7068  tcpdump_end...ph
	6384cf8: 74637064 756d7000 636f6d6d 616e646c  tcpdump.commandl
	6384d9b: 74637064 756d7020 70696420 3d202564  tcpdump pid = %d
	6384dd1: 74637064 756d7020 73657276 69636520  tcpdump service
	6384df0: 74637064 756d7020 70617261 6d657465  tcpdump paramete
	6385854: 74637064 756d705f 72657375 6c745f6c  tcpdump_result_l
	6385869: 74637064 756d702d 72657375 6c742d25  tcpdump-result-%
	6385884: 74637064 756d7000 2d767600 2d733000  tcpdump.-vv.-s0.
	63858c1: 74637064 756d705f 72657375 6c745f6c  tcpdump_result_l
	64d4b4a: 74637064 756d7000 00000000 00000000  tcpdump.........
	655482c: 74637064 756d703a 20436f75 6c646e27  tcpdump: Couldn'
	6554868: 74637064 756d703a 20436f75 6c646e27  tcpdump: Couldn'
	6ba4412: 74637064 756d7000 73797374 656d2f62  tcpdump.system/b

I've found 16 matches for the string `tcpdump`. Looking at the bytes that follow, most of these occurrences seem to be part of longer strings (eg. the match at `0x6554868`) or to be part of a cluster of NULL-terminated strings (`0x5107a9b`).

One match stands out, however. The occurrence of `tcpdump` at `0x64d4b4a` is followed by a bunch of NULLs. I know from the `struct yaffs_obj_hdr` definition that a YAFFS object's name in the filesystem is stored in a fixed-length character array, therefore seeing `tcpdump` padded with several consecutive NULLs is consistent with what I would expect to find in a header.

Let's have a closer look at the area of the dump around `0x64d4b4a`:

{% highlight objdump %}
{% include area_of_interest.txt %}
{% endhighlight %}

My `tcpdump` is preceded by `0xffff`. That's consistent with the `u16 sum_no_longer_used` in the struct declaration - if YAFFS isn't using these 16 bits, it makes sense that it would set them to 1.

I expect the previous member of the struct to be `int parent_obj_id` and the value `0x00000226` sounds like a reasonable inode number for a file system of this size. To put it differently, it's less far-fetched than if it were `0x9c36281b`

The previous member of the struct is the first one, `enum yaffs_obj_type type`. Its value here is `0x00000001` and I expect `tcpdump` to be a regular file. According to [`yaffs_guts.h`](http://www.aleph1.co.uk/gitweb?p=yaffs2.git;a=blob;f=yaffs_guts.h;hb=7e5cf0fa1b694f835cdc184a8395b229fa29f9ae#l170), the type enumeration for `yaffs_obj_type` looks like:

{% highlight c %}
enum yaffs_obj_type {
	YAFFS_OBJECT_TYPE_UNKNOWN,
	YAFFS_OBJECT_TYPE_FILE,
	YAFFS_OBJECT_TYPE_SYMLINK,
	YAFFS_OBJECT_TYPE_DIRECTORY,
	YAFFS_OBJECT_TYPE_HARDLINK,
	YAFFS_OBJECT_TYPE_SPECIAL
};
{% endhighlight %}

The value we see is indeed consistent with `YAFFS_OBJECT_TYPE_FILE`.

Based on these findings, I'm fairly confident I have a bona fide YAFFS object header starting at `0x64d4b40` in my dump. That's pretty cool.

## Chunks

I know that `0x64d4b40` is a multiple of the chunk size but I still don't know how big my dump's chunks are. In order to find out, I had to scroll down from that offset and carefully watch for patterns:

- `0x64d4b40 - 0x64d4c5f` - That's the start of the object header. Lots of NULLs used to pad `tcpdump`, followed by what kinda looks like timestamps (`0x515bcc66` works out to March 13th 2013)

- `0x64d4c60 - 0x64d537f` - Mostly just `0xff`s. What's ***very interesting*** is that these are interrupted by 16-byte fragments of non-`0xff` bytes at `0x64d4d40`, `0x64d4f50`, `0x64d5160` and `0x64d5370`

- `0x64d5380 - ...` - I've seen a lot of ELF headers [in my time](https://github.com/mattboyer/optenum) and this sure looks like one!

I don't know whether the ELF header at `0x64d5380` belongs to `tcpdump` or any other file but it looks like there's a data chunk starting at that offset. This would put the chunk size at `0x64d5380 - 0x64d4b40 = 2112` bytes.

## Spares

2112-byte chunks, eh? That's... not an integer power of 2 and therefore not a very auspicious number. 2048 would be so much better!

It just so happens that 2112 is equal to 2048 + 64 and I've found four 16-byte fragments of data in the object header that stand out from the bytes that surround them. After a week of mulling over what these mystery bytes might be, it's occurred to me that they may just be the chunk's spare data. The fact that they occur like clockwork every 512 bytes suggest they were written programmatically, as opposed to being a feature of either object header of file data.

I tried to test that hypothesis by sweeping other areas of the dump. Since I want to prove that this pattern of 16-byte fragments is ***not*** part of the data stored on the filesystem, I decided to look for it in a large area of *contiguous*, *human-readable* data.

I don't know for sure what's in the phone's `/system` directory but I can make an educated guess that there might be a copy of the [GPL](http://www.gnu.org/licenses/gpl-2.0.html) somewhere in there. Admittedly, that's stretching the definition of *human-readable* a wee bit.

	689-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ grep -iabo 'general public license' ../images/system.img | head -n 1
	102164317:General Public License

	702-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 102164317 - 102164317 % 528 ))
	102164304

	704-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ xxd -g4 -s 102164304 -l 2112 ../images/system.img
	616e750: 73206f66 20746865 20474e55 2047656e  s of the GNU Gen
	616e760: 6572616c 20507562 6c696320 4c696365  eral Public Lice
	616e770: 6e736520 76657273 696f6e20 322e0a0a  nse version 2...
	616e780: 416c7465 726e6174 6976656c 792c2074  Alternatively, t
	616e790: 68697320 736f6674 77617265 206d6179  his software may
	616e7a0: 20626520 64697374 72696275 74656420   be distributed
	616e7b0: 756e6465 72207468 65207465 726d7320  under the terms
	616e7c0: 6f662074 68650a42 5344206c 6963656e  of the.BSD licen
	616e7d0: 73652e20 53656520 52454144 4d452061  se. See README a
	616e7e0: 6e642043 4f505949 4e472066 6f72206d  nd COPYING for m
	616e7f0: 6f726520 64657461 696c732e 0a005468  ore details...Th
	616e800: 69732070 726f6772 616d2069 73206672  is program is fr
	616e810: 65652073 6f667477 6172653b 20796f75  ee software; you
	616e820: 2063616e 20726564 69737472 69627574   can redistribut
	616e830: 65206974 20616e64 2f6f7220 6d6f6469  e it and/or modi
	616e840: 66790a69 7420756e 64657220 74686520  fy.it under the
	616e850: 7465726d 73206f66 20746865 20474e55  terms of the GNU
	616e860: 2047656e 6572616c 20507562 6c696320   General Public
	616e870: 4c696365 6e736520 76657273 696f6e20  License version
	616e880: 32206173 0a707562 6c697368 65642062  2 as.published b
	616e890: 79207468 65204672 65652053 6f667477  y the Free Softw
	616e8a0: 61726520 466f756e 64617469 6f6e2e0a  are Foundation..
	616e8b0: 0a546869 73207072 6f677261 6d206973  .This program is
	616e8c0: 20646973 74726962 75746564 20696e20   distributed in
	616e8d0: 74686520 686f7065 20746861 74206974  the hope that it
	616e8e0: 2077696c 6c206265 20757365 66756c2c   will be useful,
	616e8f0: 0a627574 20574954 484f5554 20414e59  .but WITHOUT ANY
	616e900: 20574152 52414e54 593b2077 6974686f   WARRANTY; witho
	616e910: 75742065 76656e20 74686520 696d706c  ut even the impl
	616e920: 69656420 77617272 616e7479 206f660a  ied warranty of.
	616e930: 4d455243 48414e54 4142494c 49545920  MERCHANTABILITY
	616e940: 6f722046 49544e45 53532046 4f522041  or FITNESS FOR A
	616e950: ff008000 00000008 31c0f8d8 3ce1ffff  ........1...<...
	616e960: 20504152 54494355 4c415220 50555250   PARTICULAR PURP
	616e970: 4f53452e 20205365 65207468 650a474e  OSE.  See the.GN
	616e980: 55204765 6e657261 6c205075 626c6963  U General Public
	616e990: 204c6963 656e7365 20666f72 206d6f72   License for mor
	616e9a0: 65206465 7461696c 732e0a0a 00596f75  e details....You

We can see the familiar text in the dump and just when Lawrence Lessig has built up a good head of steam and starts shouting about the **MERCHANTABILITY** and the **FITNESS FOR A PARTICULAR PURPOSE**, a 16-byte fragment of data occurs at offset `0x616e950` that is definitely *not* part of the GPL.

At this point I'm fairly confident that these fragments are the out-of-band spare data written and read by YAFFS.

## Something is off

In order to make things a bit clearer, I've decided to call the combined 2112-byte blob of chunk data interleaved with spare fragments a **block**.

It looks like I've got 151040 of them in my dump:

	705-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ stat ../images/system.img 
	  File: ‘../images/system.img’
	  Size: 318996480       Blocks: 623040     IO Block: 4096   regular file
	Device: fe01h/65025d    Inode: 1066496     Links: 1
	Access: (0644/-rw-r--r--)  Uid: ( 1000/  mboyer)   Gid: ( 1000/  mboyer)
	Access: 2014-08-11 22:08:27.409957044 +0100
	Modify: 2014-06-01 03:59:00.494426437 +0100
	Change: 2014-07-06 12:47:15.303356073 +0100
	 Birth: -
	
	706-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 318996480 % 2112 ))
	0
	
	707-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 318996480 / 2112 ))
	151040

The original YAFFS spec mentions a single 16-byte spare for every chunk. Here however, I have a grand total of 64 bytes of out-of-band data for every 2048-byte chunk. Every single 16-byte fragment begins and ends with `0xff`, so I only really have 56 bytes of meaningful data in there.

Still, that's a lot more than I expected and it's obvious that the 64-*bit* `struct yaffs_tags` declaration I got from the header isn't going to map directly to the dump's spare bytes.

# Reversing the spares

Since unlike the object headers I don't *know* what the dump's spare data *should* look like, I had to find the equivalents of the `struct yaffs_tags` members in spare data the hard way.

## Finding the `obj_id`

I know that `tcpdump`'s object header has a `parent_obj_id` member with a value of `0x00000226` and I know that its parent object is a directory named `xbin`. Knowing what I know now about block sizes, I can look for that directory's object header and search the block's spare data for that number. I expect the `xbin` string to start 10 bytes from a block boundary:

	714-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ grep -abo 'xbin' ../images/system.img  | awk -F':' '{ if(10==($1 % 2112)){ print $1 - 10} }'
	105709824
	
	716-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ xxd -g4 -s 105709824 -l 80 ../images/system.img  
	64d0100: 03000000 01000000 ffff7862 696e0000  ..........xbin..
	64d0110: 00000000 00000000 00000000 00000000  ................
	64d0120: 00000000 00000000 00000000 00000000  ................
	64d0130: 00000000 00000000 00000000 00000000  ................
	64d0140: 00000000 00000000 00000000 00000000  ................


`0x00000003` is consistent with the enumerated type for a directory, my header is looking pretty groovy.

Let's put together the 4 16-byte fragments we've got around that chunk and see what we can see.

	725-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I=R=]$ for frag_offset in 512 1040 1568 2096; do xxd -g4 -s $(( 105709824 + frag_offset)) -l 16 ../images/system.img  ; done
	64d0300: ff001000 00260200 d98ba090 4fd6feff  .....&......O...
	64d0510: ff000000 0000ffff a75b4381 75a3f5ff  .........[C.u...
	64d0720: ff00001a ffffff00 2059caf5 ed0bfbff  ........ Y......
	64d0930: ff000000 ffaaaa2e 03a502ea 410bffff  ............A...

The only `0x26` byte in there is found at spare offset `0x05` and it is followed by a `0x02`. That sounds promising. I repeated this process using other files I knew the path of and was able to determine that the `obj_id`-equivalent is stored as a little-endian unsigned integer starting on the 40th bit of the spare. The YAFFS1 `struct yaffs_tags` declaration points to a length of 18 bits although there could be more here.

## Finding the `chunk_id`

According to the YAFFS spec, object header chunks have a `chunk_id` value of zero whereas file data chunks have a positive integer `chunk_id` that indicates the chunk's position in the file. There are several contiguous runs of `0x00` bytes in the `tcpdump` object header spare above. Which one's the `chunk_id`?

To find out, I had to find at least two consecutive chunks of file data and get compare their spares. I headed back to the GPL. I knew there was a 16-byte spare fragment at `0x616e950`.

	747-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 102164304 % 2112 ))
	528
	
	748-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 102164304 - 528 ))
	102163776

	750-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ for frag_offset in 512 1040 1568 2096; do xxd -g4 -s $(( 102163776 + frag_offset)) -l 16 ../images/system.img  ; done
	616e740: ff001000 00c80100 b1d3e86c 3218f9ff  ...........l2...
	616e950: ff008000 00000008 31c0f8d8 3ce1ffff  ........1...<...
	616eb60: ff000019 ffffff05 68afaa7c 4a4cfcff  ........h..|JL..
	616ed70: ff000000 faaaaa48 d1334c8c 70d3f0ff  .......H.3L.p...

	751-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 102163776 + 2112 ))
	102165888
	752-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ for frag_offset in 512 1040 1568 2096; do xxd -g4 -s $(( 102165888 + frag_offset)) -l 16 ../images/system.img  ; done
	616ef80: ff001000 00c80100 c5a1ae9d 713af0ff  ............q:..
	616f190: ff008100 00000008 39565abc 5b40f3ff  ........9VZ.[@..
	616f3a0: ff00000c ffffff0d a8b75e90 ba0bf8ff  ..........^.....
	616f5b0: ff000000 0daaaaa3 25a947e4 f8affcff  ........%.G.....

The only bytes that seem to have incremented from the first chunk's spar to the next's are at spare offset `0x12`. This is consistent with what we got from the `tcpdump` object header's spare where we have `0x00000000` at that offset. I tested that hypothesis on other files' chunks and was able to confirm that the only location in the spare where a chunkid could be found is at `0x12`. The length for that field is set to 20 bits in the YAFFS1 tags structure and could be up to 32 bits based on what I have seen.

## Finding the chunk's byte count

The last piece of information I need to successfully extract file data from my dump is the number of file data bytes in a given chunk. I know that my chunks are 2048 bytes in length, so I expect to find that value in mid-file chunks' spares. The last chunk in a given file, that is to say with a certain `obj_id`, should have a length field with a value equal to the file's length taken from the object's header modulo 2048.

	767-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ printf '%x\n' 2048
	800

There's a `0x0008` in both of my GPL spares, starting at spare offset `0x16`. The object header's spare has `0xffff` there, which makes sense since the headers don't include any file data. I set out to find `tcpdump`'s last data chunk to test that hypothesis.

I can tell from the object header above that the file's size is `0x00096b84` which is reasonable for a binary. `0x00096b84 % 2048 == 900` so I'll expect the runt chunk to have a byte count of 900. The last file chunk for `tcpdump` is in block #50363.

	790-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ echo $(( 50363 * 2112 ))
	106366656

	791-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ for frag_offset in 512 1040 1568 2096; do xxd -g4 -s $(( 106366656 + frag_offset)) -l 16 ../images/system.img  ; done
	65708c0: ff001000 00280200 f5453b63 c5b5ffff  .....(...E;c....
	6570ad0: ff002e01 00008403 324fc629 baa2f8ff  ........2O.)....
	6570ce0: ff000019 ffffff0d 7f1bae87 9e88faff  ................
	6570ef0: ff000000 f2aaaa8b 70b3f52b 746dfbff  ........p..+tm..

`0x0384` is indeed 900. I'm now quite satisfied that the chunk's byte count is stored at spare offset `0x16`.

# Conclusion

I've now reverse-engineered enough information about the layout of the `/system` dump to write a tool that will programmatically extract the contents and metadata of the filesystem. This tool is called [PYaffs](https://github.com/mattboyer/PYaffs) and I first uploaded it to GitHub about 6 weeks ago.

This is very exciting news to me because it means this blog, which is really just a side-project, has now caught up with the main event and future hacklogs will detail new developments instead of rehashing weeks-old stuff. It's nice when you break even.

Since I've now partially achieved one of the [goals]({{ site.baseurl }}{% post_url 2014-07-15-Hacklog#0 %}) I set for myself when I began, and in doing so enabled the other two, I think I should conclude with this other quote from Jurassic Park.

> It's a UNIX system, I know this!

!["It's a UNIX system"](http://i.stack.imgur.com/VSkCU.jpg)
