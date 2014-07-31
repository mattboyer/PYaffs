---
layout: post
title: "Hacklog #4: Dump format and YAFFS"
tags: yaffs spare nand python filesystem
---

# Clever title

So I [finally]({{site.baseurl}}{% post_url 2014-07-31-Hacklog#3 %}) have a raw Flash ROM dump of the partition on which my phone's `/system` filesystem [lives]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %}). I'm no longer constrained by file permissions - everything on that filesystem I now have access to.

I only need to figure out how.

## Something about YAFFS

Link to the YAFFS doc

Something about pages and spare

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


