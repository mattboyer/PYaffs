---
layout: post
title: "Hacklog #3: Down in the dumps"
tags: spflashtool flash usb
---

# Down in the dumps

I mentioned in the first post that tools exist that can be used to write/read flash for this family of devices. The most legit-looking one I found is called SPFlashTool and is available on [this site](http://mtk2000.ucoz.ru/), which looks somewhat affiliated to MediaTek.

(*TBD* try and find a legit page). The tool itself ships as part of a collection of tools named MtkDroidTools with much of the documentation in Russian.

Actually, MTKDroidTools does *NOT* have SPFlashTool. Plus, it basically automates everything else I've covered above *AS WELL* as the next post about untangling the yaffs dumps

http://forum.xda-developers.com/showthread.php?t=1982587

Something about "scatter"

There was a dialog where I entered an offset and a size - that should tie in with the last section


{% highlight bash %}
537-mboyer@marylou:~ [master:I±R=]$ lsusb
Bus 008 Device 003: ID 04f2:b2ea Chicony Electronics Co., Ltd Integrated Camera [ThinkPad]
Bus 008 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 006 Device 002: ID 04ca:2007 Lite-On Technology Corp. 
Bus 006 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
Bus 007 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 005 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
Bus 004 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 003 Device 002: ID 045e:0737 Microsoft Corp. Compact Optical Mouse 500
Bus 003 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 001 Device 025: ID 0e8d:2000 MediaTek Inc. MT65xx Preloader
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub

{% endhighlight %}
