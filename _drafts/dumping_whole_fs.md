---
layout: post
title: "Hacklog #6: Dumping the whole filesystem"
tags: VFS SSH sshd dropbear busybox netcat MTK
---

# I want it all

As of the [last post]({{site.baseurl}}{% post_url 2014-09-04-Hacklog#5 %}), I know how to use the original firmware's ``/system/xbin/su`` to get superuser privileges on the phone. That's pretty cool since it lets me access the full filesystem, but I'm still limited in the sense that I can only do this by interacting with a shell running on the phone from my [Windows VM]({{site.baseurl}}{% post_url 2014-07-16-Hacklog#1 %}) or with a terminal emulator running on the phone itself. I use Jack Palevich's [Terminal Emulator](https://play.google.com/store/apps/details?id=jackpal.androidterm) app for that and while it works very well, there's no denying that the on-screen keyboard is very tiny and the touch detection on this phone is a bit spotty which makes for a cramped and unpleasant experience. While using ``adb`` from the VM is certainly still an option, I'd prefer the comfort of using native Linux tools.

Moreover, while being able to run code from a \*nix shell on the phone is invaluable, there are things I need to do offline from a full-featured workstation where I've access to reverse-engineering tools. The analysis of ``/system/xbin/su`` is a good example of that.

In that case, I was able to get the file onto my laptop by [extracting it]({{site.baseurl}}{% post_url 2014-08-12-Hacklog#4 %}) using a custom tool from a [flash memory dump]({{site.baseurl}}{% post_url 2014-07-31-Hacklog#3 %}). Unfortunately, while PYaffs works well on the ``/system`` FS dump, I've not yet gotten it to work on the [other filesystem dumps]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %}).
In order to solve both these problems, I want to install a SSH daemon on the phone so I can connect to it wirelessly and use that to copy the entire phone filesystem for analysis.

# Allowing remote connections

While 

I first need a way to connect to the Linux OS running on the phone from another system. There's no sshd in the firmware so this is a job for [dropbear](https://matt.ucc.asn.au/dropbear/dropbear.html)

!["Dropbears!"](http://fc03.deviantart.net/fs71/f/2011/317/2/5/woot_shirt___drop_bears_v2_by_fablefire-d4g4ssa.jpg)

Dropbear illustration © [fablefire](http://fablefire.deviantart.com/art/Woot-Shirt-Drop-Bears-v2-268962490)

(deviantart link), dropbear link

Steps from sven's blog

This is nice and way more comfortable but I still need a way to copy the whole filesystem over the network

# Archiving the FS

SCP and SFTP don't work because dropbear doesn't include the respective binaries that would be needed to make them work (link to Jan's blog)

I'll do this the old school way with tar and netcat.

Unfortunately, the phone's toolbox doesn't include them.

Busybox to the rescue! Link to zoobab github repo

Final netcat CLI
