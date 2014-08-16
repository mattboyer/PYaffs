---
layout: post
title: "Hacklog #5: Hacking su(1)"
tags: su binutils
---

# gruh

fdsdfsd

Explain I've got the `/system` fs extracted and have access to the `su(1)` binary

	503-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ file su
	su: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), dynamically linked (uses shared libs), stripped


# Building binutils

I'm gonna need binutils for ARM

	./configure --prefix=$HOME/Hacks/Nam-Phone_G40C/binutils_ARM/ --disable-nls --target=arm-none-elf && make
	cd ../..
	ls
	cd -
	make install

ddffd

# Poking around the binary

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

There are some C++ symbols in there that look like they belong to some sort of Android API. The rest look like fairly bog-standard C standard library stuff. What's of particular interest here is the presence of `socket` and `bind`. These are a strong indication that this program does sockety stuff.

# Sockety stuff

{% highlight objdump %}
{% include su_objdump.txt %}
{% endhighlight %}


I have an interest in data that may hardcoded into the binary. The `.rodata` section is a good place to start


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
