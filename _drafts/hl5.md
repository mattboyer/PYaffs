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

I can see that the strings I identified above are part of the `.rodata` section. It's very likely that constant function call arguments are to be found in this section. Reverse-engineering is largely an exercise in pattern identification, it's one step removed from pareidolia and that's why reliable information is so valuable in this process - it's what anchors us to the reality of the system under study.

So yeah.


something about socket() hey, there's a call to snprintf after that. I wonder what its format string might be

See the ARM documentation for register roles and names 


	Contents of section .rodata:
	 9a24 726f2e62 75696c64 2e766572 73696f6e  ro.build.version
	 9a34 2e73646b 00300061 63746976 69747900  .sdk.0.activity.
	 9a44 616e6472 6f69642e 6170702e 49416374  android.app.IAct
	 9a54 69766974 794d616e 61676572 00737263  ivityManager.src
	 9a64 6c69622e 68757961 6e776569 2e706572  lib.huyanwei.per
	 9a74 6d697373 696f6e67 72616e74 2e726571  missiongrant.req
	 9a84 75657374 00736f63 6b65745f 61646472  uest.socket_addr
	 9a94 00756964 00706964 00737263 6c69622e  .uid.pid.srclib.
	 9aa4 68757961 6e776569 2e706572 6d697373  huyanwei.permiss
	 9ab4 696f6e67 72616e74 2e62726f 61646361  iongrant.broadca
	 9ac4 73740073 72636c69 622e6875 79616e77  st.srclib.huyanw
	 9ad4 65692e70 65726d69 7373696f 6e677261  ei.permissiongra
	 9ae4 6e742e72 6573706f 6e736500 6772616e  nt.response.gran
	 9af4 745f7265 73756c74 00557361 67653a20  t_result.Usage: 
	 9b04 7375205b 6f707469 6f6e735d 004f7074  su [options].Opt
	 9b14 696f6e73 3a002020 2d632c2d 2d636f6d  ions:.  -c,--com
	 9b24 6d616e64 20636d64 20207275 6e20636d  mand cmd  run cm
	 9b34 642e0020 202d682c 2d2d6865 6c702020  d..  -h,--help  
	 9b44 20202020 20202068 656c7000 41757468         help.Auth
	 9b54 6f723a68 7579616e 77656900 456d6169  or:huyanwei.Emai
	 9b64 6c3a7372 636c6962 40686f74 6d61696c  l:srclib@hotmail
	 9b74 2e636f6d 002f6461 74612f64 6174612f  .com./data/data/
	 9b84 7372636c 69622e68 7579616e 7765692e  srclib.huyanwei.
	 9b94 7065726d 69737369 6f6e6772 616e742f  permissiongrant/
	 9ba4 2e736f63 6b65742e 7372636c 69622e58  .socket.srclib.X
	 9bb4 58585858 58002573 002d6300 2d2d636f  XXXXX.%s.-c.--co
	 9bc4 6d6d616e 64007375 202d6320 636f6d6d  mmand.su -c comm
	 9bd4 616e6420 6572726f 722e0d00 2f737973  and error.../sys
	 9be4 74656d2f 62696e2f 73680073 68002d68  tem/bin/sh.sh.-h
	 9bf4 002d2d68 656c7000 2a236875 79616e77  .--help.*#huyanw
	 9c04 6569232a 00687579 616e7765 69206772  ei#*.huyanwei gr
	 9c14 616e7420 73756363 65737366 756c202e  ant successful .
	 9c24 2e2e0d00 2f70726f 632f2564 002f6461  ..../proc/%d./da
	 9c34 74612f64 6174612f 7372636c 69622e68  ta/data/srclib.h
	 9c44 7579616e 7765692e 7065726d 69737369  uyanwei.permissi
	 9c54 6f6e6772 616e742f 00737520 73776974  ongrant/.su swit
	 9c64 63682065 72726f72 2e0d0073 7520636f  ch error...su co
	 9c74 6d6d616e 64206572 726f722e 0d004445  mmand error...DE
	 9c84 4e590041 4c4c4f57 00                 NY.ALLOW.    
