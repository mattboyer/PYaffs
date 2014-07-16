---
layout: post
title: "Hacklog #2: Snooping around the filesystem"
tags: vfs yaffs
---

#The Virtual Filesystem

As of the [last post]({{site.baseurl}}{% post_url 2014-07-16-Hacklog#1 %}), I have the means to open an interactive shell on the phone and move around the filesystem to the extent allowed by the permissions granted to this user:

{% highlight bash %}
$ id
id
uid=2000(shell) gid=2000(shell) groups=1003(graphics),1004(input),1007(log),1009(mount),1011(adb),1015(sdcard_rw),3001(net_bt_admin),3002(net_bt),3003(inet)

$ ls -l /
ls -l /
dr-x------ root     root              2014-07-15 20:38 config
drwxrwx--- system   cache             2014-07-15 20:38 cache
lrwxrwxrwx root     root              2014-07-15 20:38 sdcard -> /mnt/sdcard
drwxr-xr-x root     root              2014-07-15 20:38 acct
drwxrwxr-x root     system            2014-07-15 20:38 mnt
lrwxrwxrwx root     root              2014-07-15 20:38 vendor -> /system/vendor
lrwxrwxrwx root     root              2014-07-15 20:38 d -> /sys/kernel/debug
lrwxrwxrwx root     root              2014-07-15 20:38 etc -> /system/etc
-rw-r--r-- root     root         4494 1970-01-01 01:00 ueventd.rc
-rw-r--r-- root     root            0 1970-01-01 01:00 ueventd.goldfish.rc
drwxr-xr-x root     root              2012-06-01 01:00 system
drwxr-xr-x root     root              2014-07-15 20:38 sys
drwxr-x--- root     root              1970-01-01 01:00 sbin
lrwxrwxrwx root     root              1970-01-01 01:00 res -> /system/res
dr-xr-xr-x root     root              1970-01-01 01:00 proc
-rw-r--r-- root     root         7451 1970-01-01 01:00 meta_init.rc
-rwxr-x--- root     root        27852 1970-01-01 01:00 init.rc
-rwxr-x--- root     root         1677 1970-01-01 01:00 init.goldfish.rc
-rwxr-x--- root     root        12110 1970-01-01 01:00 init.factory.rc
-rwxr-x--- root     root          134 1970-01-01 01:00 init.aee.customer.rc
-rwxr-x--- root     root        98396 1970-01-01 01:00 init
-rw-r--r-- root     root          141 1970-01-01 01:00 default.prop
drwxrwx--x system   system            2014-07-15 20:38 data
-rw-r--r-- root     root        26646 1970-01-01 01:00 advanced_meta_init.rc
drwx------ root     root              2013-04-03 07:17 root
drwxr-xr-x root     root              2014-07-15 20:38 dev
{% endhighlight %}

I'd very much like to inspect the contents of `init.goldfish.rc` for instance (it's an unusual name), but the user I'm logged in as is neither `root` nor a member of group `root`, so I'm SOL.

As I mentioned in the [first post]({{site.baseurl}}{% post_url 2014-07-15-Hacklog#0 %}), two of my objectives are to access the full filesystem and to obtain superuser privileges on the phone. If I can achieve the latter then I get the former "for free". Unfortunately, I'll need to know a lot about the software running on the phone to become `root` and there are areas of the filesystem I can't access using `adb shell`. It follows that I need another way to access the filesystem, unconstrained by permissions.

From messing around with portable electronices over the last ten years, I'm aware that modern phones typically have the capability to receive firmware updates *independently* of the operating system. This is usually implemented by a standalone program accessed through a key combo early in the boot process - that program would talk over USB to a specialised piece of software running on a (almost always Windows) PC and read/write a ROM image from/to the onboard flash storage. If you're really lucky, you might even get some basic debug output on the screen.

I dug around and found that such tools do indeed exist for that family of MediaTek systems, so I decided to spend some time investigating the storage configuration on this device.

# Storage

Let's have a look at what's mounted where:

{% highlight sh %}
$ mount
mount
rootfs / rootfs ro,relatime 0 0
tmpfs /dev tmpfs rw,relatime,mode=755 0 0
devpts /dev/pts devpts rw,relatime,mode=600 0 0
proc /proc proc rw,relatime 0 0
sysfs /sys sysfs rw,relatime 0 0
none /acct cgroup rw,relatime,cpuacct 0 0
tmpfs /mnt/asec tmpfs rw,relatime,mode=755,gid=1000 0 0
tmpfs /mnt/obb tmpfs rw,relatime,mode=755,gid=1000 0 0
none /dev/cpuctl cgroup rw,relatime,cpu 0 0
/dev/block/mtdblock11 /system yaffs2 ro,noatime 0 0
/dev/block/mtdblock13 /data yaffs2 rw,nosuid,nodev,relatime 0 0
/dev/block/mtdblock12 /cache yaffs2 rw,nosuid,nodev,relatime 0 0
/dev/block/mtdblock7 /system/secro yaffs2 ro,relatime 0 0
{% endhighlight %}

- [`tmpfs`](https://www.kernel.org/doc/Documentation/filesystems/tmpfs.txt) is a volatile FS backed by memory, so it's not really relevant to my interests here.

- [`rootfs`](https://www.kernel.org/doc/Documentation/filesystems/ramfs-rootfs-initramfs.txt) is also backed by memory, but unlike `tmpfs` it's populated at boot time from the contents of an archive passed to the kernel by the bootloader.

  That archive probably lives alongsides the kernel image in an area of flash ROM accessible to the bootloader. This may or may not be available once Linux is up and running on the phone. Anyway, that's something else to investigate.

- [`devpts`](https://www.kernel.org/doc/Documentation/filesystems/devpts.txt), [`proc`](https://www.kernel.org/doc/Documentation/filesystems/proc.txt), [`sysfs`](https://www.kernel.org/doc/Documentation/filesystems/sysfs.txt) and [`cgroup`](https://www.kernel.org/doc/Documentation/cgroups/cgroups.txt) are artifacts of the kernel and not used for actual data storage.

- This leaves us with 4 [`yaffs2`](http://www.yaffs.net/) filesystems backed by what looks like good, honest block devices.


