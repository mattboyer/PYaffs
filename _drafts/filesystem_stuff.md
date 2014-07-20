---
layout: post
title: "Hacklog #2: Snooping around the filesystem"
tags: vfs yaffs
---

# The Virtual Filesystem

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

# Storage configuration

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

# MTD block devices

Let's find out more about these block devices.

{% highlight bash %}
$ ls -l /dev/block
ls -l /dev/block
drwxr-xr-x root     root              2014-07-19 22:26 vold
brw------- root     root      31,  13 2014-07-19 22:26 mtdblock13
brw------- root     root      31,  12 2014-07-19 22:26 mtdblock12
brw------- root     root      31,  11 2014-07-19 22:26 mtdblock11
brw------- root     root      31,  10 2014-07-19 22:26 mtdblock10
brw------- root     root      31,   9 2014-07-19 22:26 mtdblock9
brw------- root     root      31,   8 2014-07-19 22:26 mtdblock8
brw------- root     root      31,   7 2014-07-19 22:26 mtdblock7
brw------- root     root      31,   6 2014-07-19 22:26 mtdblock6
brw------- root     root      31,   5 2014-07-19 22:26 mtdblock5
brw------- root     root      31,   4 2014-07-19 22:26 mtdblock4
brw------- root     root      31,   3 2014-07-19 22:26 mtdblock3
brw------- root     root      31,   2 2014-07-19 22:26 mtdblock2
brw------- root     root      31,   1 2014-07-19 22:26 mtdblock1
brw------- root     root      31,   0 2014-07-19 22:26 mtdblock0
brw------- root     root       7,   7 2014-07-19 22:26 loop7
brw------- root     root       7,   6 2014-07-19 22:26 loop6
brw------- root     root       7,   5 2014-07-19 22:26 loop5
brw------- root     root       7,   4 2014-07-19 22:26 loop4
brw------- root     root       7,   3 2014-07-19 22:26 loop3
brw------- root     root       7,   2 2014-07-19 22:26 loop2
brw------- root     root       7,   1 2014-07-19 22:26 loop1
brw------- root     root       7,   0 2014-07-19 22:26 loop0
{% endhighlight %}

The filesystems that are used for persistent data storage on the phone are backed by [Memory Technology Devices](http://www.linux-mtd.infradead.org/faq/general.html) devices. The FAQ I just linked to points out that MTD are neither character nor block devices, yet for the purpose of data storage they are accessed *as* block devices.

We can see that there's a grand total of 14 MTD block devices in `/dev/block`, of which only four are used for mounted filesystems. Major device number `31` is indeed claimed by the `mtdblock` driver:

{% highlight bash %}
$ cat /proc/devices
cat /proc/devices
Character devices:
  1 mem
  2 pty
  3 ttyp
  4 /dev/vc/0
  4 tty
  5 /dev/tty
  5 /dev/console
  5 /dev/ptmx
  7 vcs
 10 misc
 13 input
 29 fb
 90 mtd
108 ppp
128 ptm
136 pts
160 MT6575_VCodec
169 ttyC
176 drvb
178 ccci_fs
179 ccci_fs_util
180 usb
182 sec
183 CCCI_IPC_DEV
184 ccci
188 M4U_device
189 usb_device
190 mtk_stp_wmt
191 mtk_stp_GPS_chrdev
192 mtk_stp_BT_chrdev
193 fm
204 ttyMT
231 mtkbc
232 pvrsrvkm
233 ttyGS
234 Res_Mgr
235 DumChar
236 mt6575-SYSRAM
237 mt6575-eis
238 mt6575-isp
239 kd_camera_hw
240 mt6575-MDP
241 MTK_MAU
242 dummy_eeprom
243 kd_camera_flashlight
244 btn
245 mem_dummy
246 spc
247 MT_pmic_adc_cali
248 mt6575_jpeg
249 accdet
250 watchdog
251 mtk-adc-cali
252 BOOT
253 mt6575-fdvt
254 rtc

Block devices:
259 blkext
  7 loop
  8 sd
 31 mtdblock
 65 sd
 66 sd
 67 sd
 68 sd
 69 sd
 70 sd
 71 sd
128 sd
129 sd
130 sd
131 sd
132 sd
133 sd
134 sd
135 sd
179 mmc
254 device-mapper
{% endhighlight %}

The kernel has a `mtdblock` driver which exposes allows access to these MTD as if they were rgular block devices, but it also has a `mtd` driver used for character devices.

## The `mtdblock` driver

The phone is running version `2.6.35.7` (Yokohama) of the kernel...

{% highlight bash %}
$ cat /proc/version
cat /proc/version
Linux version 2.6.35.7 (android@ubuntu) (gcc version 4.4.3 (GCC) ) #1 PREEMPT Wed Apr 3 14:18:40 CST 2013
{% endhighlight %}

...so let's have a look at the `mtd` driver's [source](https://git.kernel.org/cgit/linux/kernel/git/stable/linux-stable.git/tree/drivers/mtd?id=ea8a52f9f4bcc3420c38ae07f8378a2f18443970) for [that version](https://git.kernel.org/cgit/linux/kernel/git/stable/linux-stable.git/tag/?id=v2.6.35.7) of the kernel. Of course, we don't know what patches may or may not have been applied at build-time but it's a good place to start.

After a bit of digging around, it emerges that:

- `mtdblock` exposes a `/proc/mtd` file [through procfs](https://git.kernel.org/cgit/linux/kernel/git/stable/linux-stable.git/tree/drivers/mtd/mtdcore.c?id=ea8a52f9f4bcc3420c38ae07f8378a2f18443970#n639):

  {% highlight bash %}
$ cat /proc/mtd
cat /proc/mtd
dev:    size   erasesize  name
mtd0: 00040000 00020000 "preloader"
mtd1: 000c0000 00020000 "dsp_bl"
mtd2: 00300000 00020000 "nvram"
mtd3: 00020000 00020000 "seccnfg"
mtd4: 00060000 00020000 "uboot"
mtd5: 00500000 00020000 "boot"
mtd6: 00500000 00020000 "recovery"
mtd7: 00120000 00020000 "secstatic"
mtd8: 00060000 00020000 "misc"
mtd9: 00300000 00020000 "logo"
mtd10: 000a0000 00020000 "expdb"
mtd11: 12700000 00020000 "system"
mtd12: 03c00000 00020000 "cache"
mtd13: 07f20000 00020000 "userdata"
  {% endhighlight %}

- `mtdblock` can [partition](https://git.kernel.org/cgit/linux/kernel/git/stable/linux-stable.git/tree/drivers/mtd/mtdpart.c?id=ea8a52f9f4bcc3420c38ae07f8378a2f18443970#n330) a MTD into smaller block devices

  {% highlight bash %}
$ cat /proc/partitions
cat /proc/partitions
major minor  #blocks  name

  31        0        256 mtdblock0
  31        1        768 mtdblock1
  31        2       3072 mtdblock2
  31        3        128 mtdblock3
  31        4        384 mtdblock4
  31        5       5120 mtdblock5
  31        6       5120 mtdblock6
  31        7       1152 mtdblock7
  31        8        384 mtdblock8
  31        9       3072 mtdblock9
  31       10        640 mtdblock10
  31       11     302080 mtdblock11
  31       12      61440 mtdblock12
  31       13     130176 mtdblock13
  {% endhighlight %}

- `mtdblock`can read partitioning information from the kernel's [command line arguments](https://git.kernel.org/cgit/linux/kernel/git/stable/linux-stable.git/tree/drivers/mtd/cmdlinepart.c?id=ea8a52f9f4bcc3420c38ae07f8378a2f18443970). Too bad I can't see what arguments were given

  {% highlight bash %}
$ ls -l /proc/cmdline
ls -l /proc/cmdline
-r--r----- root     radio           0 2014-07-20 10:11 cmdline
  {% endhighlight %}
