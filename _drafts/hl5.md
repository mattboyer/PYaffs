---
layout: post
title: "Hacklog #5: Hacking su(1)"
tags: su binutils assembly ARM nm reverse-engineering hacking
---

# A first look at su(1)

So I [now]({{site.baseurl}}{% post_url 2014-08-12-Hacklog#4 %}) have access to the full filesystem mounted under `/system` on the phone. As I stated in the very first post, I have a special interest in `/system/xbin/su`. Based on the file's name and permissions, I have a [strong expectation]({{site.baseurl}}{% post_url 2014-07-15-Hacklog#0 %}) it can be used to acquire superuser privileges.

I extracted the file using [PYaffs](https://github.com/mattboyer/PYaffs) and proceeded to inspect it.

	517-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ stat su
	  File: ‘su’
	  Size: 9820            Blocks: 24         IO Block: 4096   regular file
	Device: fe01h/65025d    Inode: 1070451     Links: 1
	Access: (0644/-rw-r--r--)  Uid: ( 1000/  mboyer)   Gid: ( 1000/  mboyer)
	Access: 2014-08-16 11:27:56.659942421 +0100
	Modify: 2014-08-02 10:23:16.973937402 +0100
	Change: 2014-08-02 10:23:16.973937402 +0100
	 Birth: -

	503-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ file su
	su: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), dynamically linked (uses shared libs), stripped

That's par for the course, there's nothing in the output of [`file(1)`](http://linux.die.net/man/1/file) here I'd call surprising.

## Building binutils for ARM

I've spent some time [poking around ELF binaries](https://github.com/mattboyer/optenum) in my day and so my first port of call was to build the excellent GNU Binutils package for the target architecture:

{% highlight bash %}
./configure --prefix=$HOME/Hacks/Nam-Phone_G40C/binutils_ARM/ --disable-nls --target=arm-none-elf && make
cd ../..
ls
cd -
make install
{% endhighlight %}

## A closer look

Since I aim to find out what it is *exactly* this `su` does, the first order of business was to find out more about the dynamic symbols it references. It's a fairly small file, weighing in at 9820 bytes and so it makes sense that much of what it does is factored out in external libraries. If these symbol refer to well-known API calls, then this would allow me to make inferences regarding the behaviour and function of the program.

Time to break out my ARM build of [`nm(1)`](http://linux.die.net/man/1/nm)!

	578-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ export PATH="$PWD/binutils_ARM/arm-none-elf/bin:${PATH}"

	581-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ nm -CD ~/Hacks/Nam-Phone_G40C/su
                 U accept
                 U __aeabi_unwind_cpp_pr0
                 U atexit
                 U atoi
                 U bind
                 U bsd_signal
        0000b200 A __bss_end__
        0000b200 A _bss_end__
        0000a1dc A __bss_start
        0000a1dc A __bss_start__
        0000a1d0 D __data_start
        0000a1e0 B __dso_handle
        0000a1dc A _edata
        0000b200 A _end
        0000b200 A __end__
                 U __errno
                 U execlp
                 U execvp
        00009ce8 A __exidx_end
        00009c8d A __exidx_start
                 U exit
        0000a010 T __FINI_ARRAY__
                 U free
                 U getppid
        0000a008 T __INIT_ARRAY__
                 U __libc_init
                 U listen
                 U malloc
                 U memcpy
                 U memset
                 U mkdir
                 U mktemp
                 U property_get
                 U putchar
                 U puts
                 U read
                 U select
                 U setgid
                 U setuid
                 U snprintf
                 U socket
                 U sprintf
        00080000 A _stack
                 U __stack_chk_fail
                 U __stack_chk_guard
                 U stat
                 U strcmp
                 U strcpy
                 U unlink
                 U android::defaultServiceManager()
        00008ed0 W android::sp<android::IBinder>::~sp()
                 U android::Parcel::writeInt32(int)
                 U android::Parcel::writeString16(unsigned short const*, unsigned int)
                 U android::Parcel::writeString16(android::String16 const&)
                 U android::Parcel::writeStrongBinder(android::sp<android::IBinder> const&)
                 U android::Parcel::writeInterfaceToken(android::String16 const&)
                 U android::Parcel::Parcel()
                 U android::Parcel::~Parcel()
                 U android::String16::String16(char const*)
                 U android::String16::~String16()
                 U android::Parcel::dataPosition() const
                 U android::Parcel::setDataPosition(unsigned int) const
                 U android::RefBase::decStrong(void const*) const

There are some C++ symbols in there that look like they belong to [some sort of Android API](http://developer.android.com/reference/android/os/Parcel.html). The rest look like fairly common C standard library stuff. What's of particular interest here is the presence of [`socket(3)`](http://linux.die.net/man/3/socket) and [`bind(3)`](http://linux.die.net/man/3/bind). These are a strong indication that this program does sockety stuff.

# Deconstructing the binary

## Something about ARM assembly

**TBD** Cover the basics of argument passing and provide links

## Disassembly

This is where the fun **really** begins. I want to get superuser privileges out of this binary. Just running `su` from an unprivileged interactive shell does *not* yield this result so I'm assuming that I need to do something else, possibly by means of a socket.

	*TBD*
	id
	su
	id

I used `objdump -Csd` to dump all sections of the `su` executable and disassemble the `.text` section into human-readable ARM assembly in one go:

{% highlight objdump %}
{% include su_objdump.txt %}
{% endhighlight %}

I can see there are human-readable strings in the `.rodata` section. It's very likely that constant function call arguments are to be found in this section. Reverse-engineering is largely an exercise in pattern identification, one step removed from pathological [pareidolia](http://en.wikipedia.org/wiki/Pareidolia) and that's why reliable information is so valuable in this process - it's what anchors us to the reality of the system under study.

So yeah. I'll have to watch out for addresses that point to `.rodata`.

The `.text` section in this file is large enough that figuring it out in its entirety would be a protracted exercise. Since what I really want is for this `su` to give me a root shell, I've decided to start from somewhere I know implements this behaviour I want and work my way back until I find out how I can trigger that.

I know thanks to `nm(1)` that my `su` has a linker table entry for [`setuid(3)`](http://linux.die.net/man/3/setuid). The output of `objdump` very conveniently includes the names of PLT entries after the BL and BLX function call instructions. As it happens, there's only one call to `setuid`, so I know that no matter what, I want to execute the instruction at offset `0x98c4`.

All that's left to do now is work my way up until I can figure out how I can cause `su` to execute this call. I've chosen to focus on the section of code in `.text` between this call and the first function header found before it, in this case the `push {r4, r5, r6, r7, lr}` at offset `0x97d8`. Here's the relevant section of disassembled ARM code:

{% highlight objdump %}
97d8:	b5f0		push	{r4, r5, r6, r7, lr}
97da:	4606		mov	r6, r0
97dc:	b0ed		sub	sp, #436	; 0x1b4
97de:	4d7a		ldr	r5, [pc, #488]	; (99c8 <android::sp<android::IBinder>::~sp()+0xaf8>)
97e0:	460f		mov	r7, r1
97e2:	447d		add	r5, pc
97e4:	4979		ldr	r1, [pc, #484]	; (99cc <android::sp<android::IBinder>::~sp()+0xafc>)
97e6:	5868		ldr	r0, [r5, r1]
97e8:	2e02		cmp	r6, #2
97ea:	6803		ldr	r3, [r0, #0]
97ec:	936b		str	r3, [sp, #428]	; 0x1ac
97ee:	d10e		bne.n	980e <android::sp<android::IBinder>::~sp()+0x93e>
97f0:	687c		ldr	r4, [r7, #4]
97f2:	4977		ldr	r1, [pc, #476]	; (99d0 <android::sp<android::IBinder>::~sp()+0xb00>)
97f4:	4620		mov	r0, r4
97f6:	4479		add	r1, pc
97f8:	f7ff eaf4	blx	8de4 <strcmp@plt>
97fc:	b128		cbz	r0, 980a <android::sp<android::IBinder>::~sp()+0x93a>
97fe:	4975		ldr	r1, [pc, #468]	; (99d4 <android::sp<android::IBinder>::~sp()+0xb04>)
9800:	4620		mov	r0, r4
9802:	4479		add	r1, pc
9804:	f7ff eaee	blx	8de4 <strcmp@plt>
9808:	b908		cbnz	r0, 980e <android::sp<android::IBinder>::~sp()+0x93e>
980a:	f7ff fe93	bl	9534 <android::sp<android::IBinder>::~sp()+0x664>
980e:	1c72		adds	r2, r6, #1
9810:	4c71		ldr	r4, [pc, #452]	; (99d8 <android::sp<android::IBinder>::~sp()+0xb08>)
9812:	0090		lsls	r0, r2, #2
9814:	447c		add	r4, pc
9816:	f844 6cf4	str.w	r6, [r4, #-244]
981a:	f7ff eb02	blx	8e20 <malloc@plt>
981e:	f844 0cf0	str.w	r0, [r4, #-240]
9822:	b188		cbz	r0, 9848 <android::sp<android::IBinder>::~sp()+0x978>
9824:	f854 2cf4	ldr.w	r2, [r4, #-244]
9828:	1c51		adds	r1, r2, #1
982a:	008a		lsls	r2, r1, #2
982c:	2100		movs	r1, #0
982e:	f7ff ea2c	blx	8c88 <memset@plt>
9832:	f854 3cf4	ldr.w	r3, [r4, #-244]
9836:	f854 0cf0	ldr.w	r0, [r4, #-240]
983a:	009a		lsls	r2, r3, #2
983c:	4639		mov	r1, r7
983e:	f7ff eaf6	blx	8e2c <memcpy@plt>
9842:	2e01		cmp	r6, #1
9844:	dc03		bgt.n	984e <android::sp<android::IBinder>::~sp()+0x97e>
9846:	e012		b.n	986e <android::sp<android::IBinder>::~sp()+0x99e>
9848:	f844 0cf4	str.w	r0, [r4, #-244]
984c:	e0ab		b.n	99a6 <android::sp<android::IBinder>::~sp()+0xad6>
984e:	4963		ldr	r1, [pc, #396]	; (99dc <android::sp<android::IBinder>::~sp()+0xb0c>)
9850:	6878		ldr	r0, [r7, #4]
9852:	4479		add	r1, pc
9854:	f7ff eac6	blx	8de4 <strcmp@plt>
9858:	4606		mov	r6, r0
985a:	b940		cbnz	r0, 986e <android::sp<android::IBinder>::~sp()+0x99e>
985c:	4860		ldr	r0, [pc, #384]	; (99e0 <android::sp<android::IBinder>::~sp()+0xb10>)
985e:	4478		add	r0, pc
9860:	f7ff ea72	blx	8d48 <puts@plt>
9864:	4630		mov	r0, r6
9866:	f7ff eae8	blx	8e38 <setgid@plt>
986a:	b358		cbz	r0, 98c4 <android::sp<android::IBinder>::~sp()+0x9f4>
986c:	e02d		b.n	98ca <android::sp<android::IBinder>::~sp()+0x9fa>
986e:	f7ff eaea	blx	8e44 <getppid@plt>
9872:	ae1b		add	r6, sp, #108	; 0x6c
9874:	2100		movs	r1, #0
9876:	f44f 7280	mov.w	r2, #256	; 0x100
987a:	4c5a		ldr	r4, [pc, #360]	; (99e4 <android::sp<android::IBinder>::~sp()+0xb14>)
987c:	447c		add	r4, pc
987e:	6060		str	r0, [r4, #4]
9880:	4630		mov	r0, r6
9882:	f7ff ea02	blx	8c88 <memset@plt>
9886:	6862		ldr	r2, [r4, #4]
9888:	4630		mov	r0, r6
988a:	4957		ldr	r1, [pc, #348]	; (99e8 <android::sp<android::IBinder>::~sp()+0xb18>)
988c:	4479		add	r1, pc
988e:	466f		mov	r7, sp
9890:	f7ff eade	blx	8e50 <sprintf@plt>
9894:	4630		mov	r0, r6
9896:	4669		mov	r1, sp
9898:	f7ff eae0	blx	8e5c <stat@plt>
989c:	2240		movs	r2, #64	; 0x40
989e:	9e06		ldr	r6, [sp, #24]
98a0:	2100		movs	r1, #0
98a2:	6026		str	r6, [r4, #0]
98a4:	ae5b		add	r6, sp, #364	; 0x16c
98a6:	4630		mov	r0, r6
98a8:	f7ff e9ee	blx	8c88 <memset@plt>
98ac:	f44f 71fc	mov.w	r1, #504	; 0x1f8
98b0:	484e		ldr	r0, [pc, #312]	; (99ec <android::sp<android::IBinder>::~sp()+0xb1c>)
98b2:	4478		add	r0, pc
98b4:	f7ff ead8	blx	8e68 <mkdir@plt>
98b8:	f7ff fe68	bl	958c <android::sp<android::IBinder>::~sp()+0x6bc>
98bc:	60a0		str	r0, [r4, #8]
98be:	2800		cmp	r0, #0
98c0:	da33		bge.n	992a <android::sp<android::IBinder>::~sp()+0xa5a>
98c2:	e02d		b.n	9920 <android::sp<android::IBinder>::~sp()+0xa50>
98c4:	f7ff ead6	blx	8e74 <setuid@plt> ; <--- I want this!


98c8:	b110		cbz	r0, 98d0 <android::sp<android::IBinder>::~sp()+0xa00>
98ca:	4849		ldr	r0, [pc, #292]	; (99f0 <android::sp<android::IBinder>::~sp()+0xb20>)
98cc:	4478		add	r0, pc
98ce:	e01b		b.n	9908 <android::sp<android::IBinder>::~sp()+0xa38>
{% endhighlight %}

## Working back

The instruction immediately preceding the call to `setuid(3)` is a `b.n` unconditional branch and the one before *that* is a `bge.n` conditional branch. This is a pattern typical of compiled code that is found at the "seams" between sequences of instructions compiled from different control flow branches. The upshot is that if and when the ARM CPU executes the instruction at offset `0x98c4`, it must be after it's jumped there from somewhere else.

Sure enough, there's a `cbz` conditional branching instruction that points here at offset `0x986a`:

{% highlight objdump %}
985c:        4860              ldr        r0, [pc, #384]        ; (99e0 <android::sp<android::IBinder>::~sp()+0xb10>)
985e:        4478              add        r0, pc
9860:        f7ff ea72         blx        8d48 <puts@plt>
9864:        4630              mov        r0, r6
9866:        f7ff eae8         blx        8e38 <setgid@plt>
986a:        b358              cbz        r0, 98c4 <android::sp<android::IBinder>::~sp()+0x9f4>
{% endhighlight %}

So that makes sense, right? First we set the effective Group ID with [`setgid(3)`](http://linux.die.net/man/3/setgid) then if that returned 0, we move on to the effective UID. We even reuse the `0` return code from `setgid` as `setuid`'s argument.

The GID is loaded into `r0` from `r6` at `0x9864`. Before that, we have a call to [`puts(3)`](http://linux.die.net/man/3/puts). The argument given to `puts` in `r0` is `*0x99e0(==0x03a7) + 0x985e + 0x4 == 0x9c09`, which points to a string in `.rodata`: "`huyanwei grant successful ...\n`". Looks like we're on the right track, alright!

This call to `puts(3)` is preceded by a call to `strcmp(3)` and a `cbnz` conditional branch instruction:

{% highlight objdump %}
984e:        4963              ldr        r1, [pc, #396]        ; (99dc <android::sp<android::IBinder>::~sp()+0xb0c>)
9850:        6878              ldr        r0, [r7, #4]
9852:        4479              add        r1, pc
9854:        f7ff eac6         blx        8de4 <strcmp@plt>
9858:        4606              mov        r6, r0
985a:        b940              cbnz       r0, 986e <android::sp<android::IBinder>::~sp()+0x99e>
{% endhighlight %}

This is very promising, as it means a zero return value in this call to [`strcmp(3)`](http://linux.die.net/man/3/strcmp) is what triggers the privilege escalation performed by `setgid` then `setuid`.

So what are we comparing, and against what? The second argument passed to `strcmp` in `r1` is a static `char*` with a value of `*0x99dc(==0x03a6) + 0x9852 + 0x4 == 0x9bfc`. This once again points to a string in `.rodata` with the value "`*#huyanwei#*`". This includes the name of the author and looks like some sort of hardcoded passphrase. But what are we comparing against this value? The immediate answer is `*(r7+4)` but what is at that address?

To find out more, I searched for instructions before the call to `strcmp` that involve the `r7` register. There's a `mov r1, r7` at offset `0x983c` where we use `r7` as the second argument in a call to [`memcpy(3)`](http://linux.die.net/man/3/memcpy), ie. as the source. Before that, we have the following:

{% highlight objdump %}
97f0:        687c              ldr        r4, [r7, #4]
97f2:        4977              ldr        r1, [pc, #476]        ; (99d0 <android::sp<android::IBinder>::~sp()+0xb00>)
97f4:        4620              mov        r0, r4
97f6:        4479              add        r1, pc
97f8:        f7ff eaf4         blx        8de4 <strcmp@plt>
97fc:        b128              cbz        r0, 980a <android::sp<android::IBinder>::~sp()+0x93a>
97fe:        4975              ldr        r1, [pc, #468]        ; (99d4 <android::sp<android::IBinder>::~sp()+0xb04>)
9800:        4620              mov        r0, r4
9802:        4479              add        r1, pc
9804:        f7ff eaee         blx        8de4 <strcmp@plt>
9808:        b908              cbnz       r0, 980e <android::sp<android::IBinder>::~sp()+0x93e>
980a:        f7ff fe93         bl         9534 <android::sp<android::IBinder>::~sp()+0x664>
{% endhighlight %}

So we copy `*(r7 + 4)` - the same address we'll compare against `*#huyanwei#*` to decide whether to escalate privileges - into `r4` and then `r0`. This becomes the first argument passed in another call to `strcmp` at offset `0x97f8`. What's the second argument, then? `*0x99d0 (==0x3f8) + 0x97f6 + 4 == 0x9bf2`, which points to a string in `.rodata`: "`-h`".

Wait a minute! That looks a lot like one of the CLI options documented in the usage message, doesn't it? If `*(r7 + 4)` is indeed equal to "`-h`" then we jump to `0x980a`, else we compare that address again, this time to `*0x99d4 (==0x3ef) + 0x9802 + 4 == 0x9bf5`. Once again, this points to `.rodata` and this time to "`--help`". We can now reasonably infer that `r7 + 4` points to the first CLI argument given to `su`. Considering we have `mov r7, r1` at offset `0x97e0` immediately after the function header, this would mean that -***GASP!***- `r1` was `argv` when the function was called!

Since we're looking at 32-bit ARM code, `argv + 4 == argv[1]`. This would make the function starting at `0x97d8` the program's `main` and `r0` our `argc`.

## Let's try it out

I tried running su with `*#huyanwei#*` as the first argument on the CLI:

...and it worked. Yay!


# Sockety stuff

The above looks like a read loop where we wait for read (whatever the file descriptor actually points to) to return something negative. The file descriptor for the call to read() is in `r0`, the value of which is the return value of the function called at `0x97b4`. What we have at 0x966c looks like it ties in with the sockety stuff (there are calls to `select`)

TODO The value of `pc` is address of the instruction in the objdump + 4 (because we're reading Thumb code as per the ELF header)

The parcel stuff is explained here: http://developer.android.com/reference/android/os/Parcel.html

# More shite

I ran [`strings(1)`](http://linux.die.net/man/1/strings) on the file to see what bits of human-readable text might be in there:

	566-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ strings --radix=x -n 8 ./su
	    114 /system/bin/linker
	    6c5 __aeabi_unwind_cpp_pr0
	    6dc __stack_chk_fail
	    6ed __stack_chk_guard
	    707 snprintf
	    739 __dso_handle
	    746 __INIT_ARRAY__
	    755 __FINI_ARRAY__
	    764 __exidx_start
	    772 __exidx_end
	    77e __data_start
	    792 __bss_start
	    79e __bss_start__
	    7ac _bss_end__
	    7b7 __bss_end__
	    7f4 property_get
	    822 _ZNK7android7RefBase9decStrongEPKv
	    845 _ZN7android8String16D1Ev
	    85e _ZN7android6Parcel13writeString16ERKNS_8String16E
	    890 _ZNK7android6Parcel15setDataPositionEj
	    8b7 _ZN7android6Parcel10writeInt32Ei
	    8d8 _ZN7android6ParcelC1Ev
	    8ef _ZN7android6ParcelD1Ev
	    906 _ZN7android2spINS_7IBinderEED1Ev
	    927 _ZN7android6Parcel19writeInterfaceTokenERKNS_8String16E
	    95f _ZN7android6Parcel17writeStrongBinderERKNS_2spINS_7IBinderEEE
	    99d _ZN7android8String16C1EPKc
	    9b8 _ZNK7android6Parcel12dataPositionEv
	    9dc _ZN7android21defaultServiceManagerEv
	    a01 _ZN7android6Parcel13writeString16EPKtj
	    a2e __libc_init
	    a63 bsd_signal
	    a89 liblog.so
	    a93 libsqlite.so
	    aa0 libcutils.so
	    aad libbinder.so
	    aba libutils.so
	    ace libstdc++.so
	   17f0 |hwI FyD
	   1879 rZL|D``0F
	   1886 bh0FWIyDoF
	   190e <H<IxDyD
	   1a24 ro.build.version.sdk
	   1a3b activity
	   1a44 android.app.IActivityManager
	   1a61 srclib.huyanwei.permissiongrant.request
	   1a89 socket_addr
	   1a9d srclib.huyanwei.permissiongrant.broadcast
	   1ac7 srclib.huyanwei.permissiongrant.response
	   1af0 grant_result
	   1afd Usage: su [options]
	   1b11 Options:
	   1b1a   -c,--command cmd  run cmd.
	   1b37   -h,--help         help
	   1b50 Author:huyanwei
	   1b60 Email:srclib@hotmail.com
	   1b79 /data/data/srclib.huyanwei.permissiongrant/.socket.srclib.XXXXXX
	   1bc0 --command
	   1bca su -c command error.
	   1be0 /system/bin/sh
	   1bfc *#huyanwei#*
	   1c09 huyanwei grant successful ...
	   1c28 /proc/%d
	   1c31 /data/data/srclib.huyanwei.permissiongrant/
	   1c5d su switch error.
	   1c6f su command error.

The early strings in there are consistent with a symbol table, it's the strings at the end that are interesting. In particular, there are several instances of `huyanwei` in there and it looks like it's the name of the person who wrote this implementation of `su(1)`.



I did a teeny bit of searching online and there *are* pages that reference this name, however they are mostly in Chinese which I cannot read. I chose not to spend too much time searching for third-party information as I know from bitter experience that nothing kills momentum on a little project like this quite like stumbling upon the answers.
