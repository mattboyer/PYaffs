---
layout: post
title: "Hacklog #4: Dump format and YAFFS"
tags: yaffs spare nand python filesystem
---

# Leitmotiv

Well over twenty years ago, the movie [Jurassic Park](http://www.imdb.com/title/tt0107290/) came out. There's a lot of exposition in the first third of that movie. In particular, there's a scene where a small group of people is given access -for the first time!- to an area of the island where very large dinosaurs roam free.

Among them is a man who is some sort of scientist and definitely not a people person. They happen upon a dino-sized dump of dino-poo and yer man deadpans:

> That is one big pile of shit.

!["That is one big pile of shit"](http://static2.hypable.com/wp-content/uploads/2013/04/jurassic.park_.poo_.png)

He's not alone, of course. Accompanying him on the tour is Dr Sattler, a paleobotanist. Dr Sattler takes a keen interest in how plant life has been recreated in the park and seizes the opportunity to take samples:

!["Reverse-engineering"](http://hellogiggles.com/wp-content/uploads/2013/01/23/triceratops2.jpg)

That scene, and this picture in particular, is both the theme and summary of this post

# Let's get started

So I [finally]({{site.baseurl}}{% post_url 2014-07-31-Hacklog#3 %}) have a raw Flash ROM dump of the partition on which my phone's `/system` filesystem [lives]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %}). I'm no longer constrained by file permissions - everything on that filesystem I now have access to.

I only need to figure out how.

## YAFFS

As I saw in the output of mount(1), `/system` is a `yaffs2` filesystem, mounted read-only:

	$ mount
	
	/dev/block/mtdblock11 /system yaffs2 ro,noatime 0 0

[`yaffs2`](http://www.yaffs.net/yaffs-2-specification) is the second revision of [`yaffs`](http://www.yaffs.net/yaffs-original-specification), a Flash-optimised filesystem that's been around a while.

In order to access the filesystem's contents out-of-band, I had to spend some time reading and digesting both filesystems' specification documents. The yaffs2 spec is not a standalone document so familiarity with yaffs stuff is pretty much required.

Something about object headers

Something about chunks

It's pretty important to get the terminology right here, and to be consistent

## Gruh

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
