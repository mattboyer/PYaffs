---
layout: post
title: "Hacklog #4: Dump format and YAFFS"
tags: yaffs spare nand python filesystem
---

# Leitmotiv

Well over twenty years ago, the movie [Jurassic Park](http://www.imdb.com/title/tt0107290/) came out. I remember there was a lot of exposition in the first act. In particular, there's a scene where a small group of people is given access -for the first time!- to an area of the island where very large dinosaurs roam free.

Among them is a man who is some sort of scientist and definitely not a people person. They happen upon a dino-sized *dump* of dino poo and yer man deadpans:

> That is one big pile of shit.

!["That is one big pile of shit"]({{ site.baseurl }}/images/BPOS.jpg)

He's not alone, of course. Accompanying him on the tour is Dr Sattler, a paleobotanist. Dr Sattler takes a keen interest in how plant life has been recreated in the park and seizes the opportunity to take samples:

!["Reverse-engineering"]({{ site.baseurl }}/images/reverse_engineering.jpg)

That scene, and this picture in particular, is both the theme and summary of this post.

Reverse engineering is a dirty job but someone's gotta do it.

# Let's get started

So I [finally]({{site.baseurl}}{% post_url 2014-07-31-Hacklog#3 %}) have a raw Flash ROM dump of the partition on which my phone's `/system` filesystem [lives]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %}). I'm no longer constrained by file permissions - everything on that filesystem I now have access to.

I only need to figure out how.

## YAFFS

As I saw in the output of mount(1), `/system` is a `yaffs2` filesystem, mounted read-only:

	$ mount
	
	/dev/block/mtdblock11 /system yaffs2 ro,noatime 0 0

[`yaffs2`](http://www.yaffs.net/yaffs-2-specification) is the second revision of [`yaffs`](http://www.yaffs.net/yaffs-original-specification), a Flash-optimised filesystem that's been around a while.

My first idea was to open the `/system` dump with a YAFFS access tool. None of them worked with the dumps I got out of my phone and this little project lost momentum and got stalled at that point for three months.

I eventually picked it up again and decided to do this the hard way. In order to access the filesystem's contents out-of-band, I had to spend time reading and digesting both filesystems' specification documents. The `yaffs2` spec is not a standalone document so familiarity with YAFFS stuff is pretty much required.

### A YAFFS primer

The basic unit of data storage in YAFFS is a **chunk**. A chunk may contain *either* filesystem stuff of the kind displayed by [`stat(1)`](http://linux.die.net/man/1/stat) (viz. inodes, file names, permissions, etc.) *or* file data.

Within the scope of the YAFFS documentation, filesystem entities such as files and directories are called **objects**. Every object has its metadata stored in a dedicated chunk in a data structure the YAFFS documentation calls an **object header**

The format for object headers is defined in `yaffs_guts.h` in the form of a [plain old C struct](http://www.aleph1.co.uk/gitweb?p=yaffs2.git;a=blob;f=yaffs_guts.h;h=231f8ac567eb86e3583f4c1fc436e9c89a4ca2c8;hb=HEAD#l312):

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

A given file may be split across several data chunks, in addition to its header chunk. Since the object header format doesn't have any references to other chunks, it follows that some sort of metadata is needed around data chunks for the filesystem implementation to know what file a given chunk belongs to, and where that chunk falls in the ordered list of data chunks that comprise the whole file. This data is stored in what the YAFFS docs call **spare** data. The docs mention that spare data is interleaved with "actual" chunk data but doesn't say much more beyond that.

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

- `obj_id` - That's our object identifier - this lets us know which filesystem "entity" a given chunk belongs to. I think of that numeric identifier as an [*inode number*](http://www.linfo.org/inode.html).

- `chunk_id` - This is effectively the chunk's position in the ordered list of chunks that, together, hold the file's contents.

- `n_bytes_lsb` and `n_bytes_msb` - Together, these tell us how many bytes of *actual file data* are in the chunk. Unless a file's size happens to be a whole multiple of the chunk size, we'll need to know where to cut off the runt chunk.

- `ecc` - Just some extra redundancy bits derived from the tags themselves. This isn't very interesting to me.

- `serial_number` - Who knows?



## Things get confusing

I focused on the YAFFS definition of tag data above, even though the `/system` dump I have is taken from a YAFFS2 filesystem.
Interestingly, the number of bytes in a chunk is stored on 10 + 2 bits, meaning that there can be up to 4095

Something about object headers


It's pretty important to get the terminology right here, and to be consistent

## First part

### Chunk size

How did I figure out chunk size was 2048 bytes?

### Starting point

objectheaders as starting points as they are big, easy to identify and I can get a high degree of confidence that the way I parse them is correct

Then: Use the parent objectid field from the objectheader of a file with a known path to know what to look for in the spares of the parent. This assumes the chunk containing the parent's header is known

# Gruh

And what better way to get started than to have a look using a hex editor?

{% highlight sh %}
534-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [HL4:I±R=]$ xxd -g4 ../images/system.img | head -n 825
{% include system_head.txt %}
{% endhighlight %}

The following patterns emerge:

- Every 512 bytes, there is a 16-byte chunk of data that seems to always start and end with `ff`


# Conclusion

> It's a UNIX system, I know this!

!["It's a UNIX system"](http://i.stack.imgur.com/VSkCU.jpg)

Yes it is, yes it is.
