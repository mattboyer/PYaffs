---
layout: post
title: "Hacklog #5: Hacking su(1)"
tags: su binutils assembly ARM
---

# TBD clever title involving the word 'binary'

So I now have access to the full `/system` filesystem. As I stated in the very first post, I have a special interest in `/system/xbin/su`. Based on the file's name and permissions, I have a [strong expectation]({{site.baseurl}}{% post_url 2014-07-15-Hacklog#0 %}) it can be used to acquire superuser privileges.

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

That's par for the course, there's nothing in the output of [`file(1)`](http://linux.die.net/man/1/file) here I'd call surprising. I ran [`strings(1)`](http://linux.die.net/man/1/strings) on the file to see what bits of human-readable text might be in there:

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

# Further investigation with binutils

## Building binutils for ARM

I've spent some time [poking around ELF binaries](https://github.com/mattboyer/optenum) in my day and so my first port of call was to build the excellent GNU Binutils package for the target architecture:

{% highlight bash %}
./configure --prefix=$HOME/Hacks/Nam-Phone_G40C/binutils_ARM/ --disable-nls --target=arm-none-elf && make
cd ../..
ls
cd -
make install
{% endhighlight %}

## Poking around the binary

Since I aim to find out what it is *exactly* this `su` does, the first order of business was to find out more about the dynamic symbols it references. It's a fairly small file, weighing in at 9820 bytes and so it makes sense that much of what it does is factored out in external libraries. If these symbol refer to well-known API calls, then this would allow me to make inferences regarding the behaviour and function of the program.

Time to break out my ARM build of [`nm(1)`](http://linux.die.net/man/1/nm)! I turned on symbol demangling with `-C` based on the output of `strings(1)` above:

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

There are some C++ symbols in there that look like they belong to some sort of Android API. The rest look like fairly common C standard library stuff. What's of particular interest here is the presence of [`socket(3)`](http://linux.die.net/man/3/socket) and [`bind(3)`](http://linux.die.net/man/3/bind). These are a strong indication that this program does sockety stuff.

## Disassembly

This is where the fun **really** begins. I want to get superuser privileges out of this binary. Just running `su` from an unprivileged interactive shell does *not* yield this result so I'm assuming that I need to do something else, possibly by means of a socket.

I used `objdump -Csd` to dump all sections of the `su` executable and disassemble the `.text` section into human-readable ARM assembly in one go:

{% highlight objdump %}
{% include su_objdump.txt %}
{% endhighlight %}

I can see that the strings I identified above are part of the `.rodata` section. It's very likely that constant function call arguments are to be found in this section. Reverse-engineering is largely an exercise in pattern identification, one step removed from pathological [pareidolia](http://en.wikipedia.org/wiki/Pareidolia) and that's why reliable information is so valuable in this process - it's what anchors us to the reality of the system under study.

So yeah. `.rodata`.


# I've no idea what I'm doing

There's a call to a function named `property_get` at `0x9250`:

{% highlight objdump %}
9244:    48b2          ldr    r0, [pc, #712]    ; (9510 <android::sp<android::IBinder>::~sp()+0x640>)
9246:    4621          mov    r1, r4
9248:    4478          add    r0, pc
924a:    4ab2          ldr    r2, [pc, #712]    ; (9514 <android::sp<android::IBinder>::~sp()+0x644>)
924c:    447a          add    r2, pc
924e:    ae23          add    r6, sp, #140    ; 0x8c
9250:    f7ff ed20     blx    8c94 <property_get@plt>
{% endhighlight %}

As per the ARM argument passing convention, the first 4 args are passed in registers `r0` through `r3`, in order. What's in our `r0` here? At offset `0x9244`, we load the value found 712 bytes past the program counter, ie at `0x9246 + 712 == 0x950e`:

    9500 bde8f08f 424e444c fcffffff e20e0000  ....BNDL........
    9510 d8070000 e9070000 cb070000 9a070000  ................

The 4 bytes at `0x950e` are `0x000007d8`. We add the value of `pc` to `r0` at `0x9248` (the Program Counter has already been incremented to the next address) so that `r0` has the value `0x924a + 0x7d8 == 0x9a24`. This points to a hardcoded string in `.rodata`, "`ro.build.version.sdk`":

    9a24 726f2e62 75696c64 2e766572 73696f6e  ro.build.version
    9a34 2e73646b 00300061 63746976 69747900  .sdk.0.activity.


That's nice but not very useful.


OK, let's try from setuid instead

    98c4:	f7ff ead6 	blx	8e74 <setuid@plt>

There's a branching instruction that points here:

    9866:	f7ff eae8 	blx	8e38 <setgid@plt>
    986a:	b358      	cbz	r0, 98c4 <android::sp<android::IBinder>::~sp()+0x9f4>

So that makes sense, right? First we set the effective Group ID then if that returned 0, we move on to the effective UID.

Let's make our way up:

    983e:	f7ff eaf6 	blx	8e2c <memcpy@plt>
    9842:	2e01      	cmp	r6, #1
    9844:	dc03      	bgt.n	984e <android::sp<android::IBinder>::~sp()+0x97e>
    9846:	e012      	b.n	986e <android::sp<android::IBinder>::~sp()+0x99e>
    9848:	f844 0cf4 	str.w	r0, [r4, #-244]
    984c:	e0ab      	b.n	99a6 <android::sp<android::IBinder>::~sp()+0xad6>
    984e:	4963      	ldr	r1, [pc, #396]	; (99dc <android::sp<android::IBinder>::~sp()+0xb0c>)
    9850:	6878      	ldr	r0, [r7, #4]
    9852:	4479      	add	r1, pc
    9854:	f7ff eac6 	blx	8de4 <strcmp@plt>
    9858:	4606      	mov	r6, r0
    985a:	b940      	cbnz	r0, 986e <android::sp<android::IBinder>::~sp()+0x99e>
    985c:	4860      	ldr	r0, [pc, #384]	; (99e0 <android::sp<android::IBinder>::~sp()+0xb10>)
    985e:	4478      	add	r0, pc
    9860:	f7ff ea72 	blx	8d48 <puts@plt>
    9864:	4630      	mov	r0, r6
    9866:	f7ff eae8 	blx	8e38 <setgid@plt>

    99e0:	03a7      	lsls	r7, r4, #14


The GID is loaded into `r0` from `r6`. Before that , we have a call to puts. The argument given to puts is `0x03a7 + 0x985e + 0x4 == 0x9c09` "`huyanwei grant successful ...\n`". Looks like we're on the right track alright!

The GID is loaded into r0 from r6 at 9864. Before that r6 is overwritten with r0 at 0x9858 at which point r0 holds the return value of a call to strcmp.

The second arg given to strcmp is *0x99de=0x03a7 + 0x9852 + 4 = 0x9bfd "`*#huyanwei#*`". That looks like some sort of hardcoded passphrase. So far, so promising. But what's the first argument? r0 is loaded with the value at r7-4



    97b2:	4628      	mov	r0, r5
    97b4:	f7ff ff5a 	bl	966c <android::sp<android::IBinder>::~sp()+0x79c>
    97b8:	2800      	cmp	r0, #0
    97ba:	db0a      	blt.n	97d2 <android::sp<android::IBinder>::~sp()+0x902>
    97bc:	223f      	movs	r2, #63	; 0x3f
    97be:	4621      	mov	r1, r4
    97c0:	f7ff eb28 	blx	8e14 <read@plt>
    97c4:	2800      	cmp	r0, #0
    97c6:	db04      	blt.n	97d2 <android::sp<android::IBinder>::~sp()+0x902>
    97c8:	d0f3      	beq.n	97b2 <android::sp<android::IBinder>::~sp()+0x8e2>

The above looks like a read loop where we wait for read (whatever the file descriptor actually points to) to return something negative. The file descriptor for the call to read() is in `r0`, the value of which is the return value of the function called at `0x97b4`. What we have at 0x966c looks like it ties in with the sockety stuff (there are calls to `select`)

TODO The value of `pc` is address of the instruction in the objdump + 4 (because we're reading Thumb code as per the ELF header)

The parcel stuff is explained here: http://developer.android.com/reference/android/os/Parcel.html
