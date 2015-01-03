---
layout: post
title: "Hacklog #6: Dumping the whole filesystem"
tags: VFS SSH sshd dropbear busybox netcat MTK
---

# I want it all

As of the [last post]({{site.baseurl}}{% post_url 2014-09-04-Hacklog#5 %}), I know how to use the original firmware's `/system/xbin/su` to get superuser privileges on the phone. That's pretty cool since it lets me access the full filesystem, but I'm still limited in the sense that I can only do this by interacting with a shell running on the phone from my [Windows VM]({{site.baseurl}}{% post_url 2014-07-16-Hacklog#1 %}) or with a terminal emulator running on the phone itself. I use Jack Palevich's [Terminal Emulator](https://play.google.com/store/apps/details?id=jackpal.androidterm) app for that and while it works very well, there's no denying that the on-screen keyboard is very tiny and the touch detection on this phone is a bit spotty which makes for a cramped and unpleasant experience. While using `adb` from the VM is certainly still an option, I'd prefer the comfort of using native Linux tools.

Moreover, while being able to run code from a \*nix shell on the phone is invaluable, there are things I need to do offline from a full-featured workstation where I've access to reverse-engineering tools. The analysis of `/system/xbin/su` is a good example of that.

In that case, I was able to get the file onto my laptop by [extracting it]({{site.baseurl}}{% post_url 2014-08-12-Hacklog#4 %}) using a custom tool from a [flash memory dump]({{site.baseurl}}{% post_url 2014-07-31-Hacklog#3 %}). Unfortunately, while PYaffs works well on the `/system` FS dump, I've not yet gotten it to work on the [other filesystem dumps]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %}).

In order to solve both these problems, I want to install a SSH daemon on the phone so I can connect to it wirelessly and use that to copy the entire phone filesystem for analysis.

# Allowing remote connections

The `/system` dump I extracted includes a bunch of interesting CLI executables, most of which are implemented by an all-in-one binary, `/system/bin/toolbox`.

```
{% include system_file_list.txt %}
```

Unfortunately, while there are some pretty powerful tools in there I couldn't find a SSH daemon in the original firmware. Using the [OpenSSH](http://www.openssh.com/) implementation of the [Secure SHell protocol](http://datatracker.ietf.org/wg/secsh/documents/) would be possible but this would require me to cross-compile it from my `x86_64` laptop for the phone's target architecture, `arm-*-elf`... along with its dependencies, including OpenSSL's libcrypto.

This would be a significant effort, so I chose instead to use  [dropbear](https://matt.ucc.asn.au/dropbear/dropbear.html), a more lightweight SSH daemon. For fun, here's a comparison of runtime dependencies for OpenSSH's [`sshd`](http://www.openbsd.org/cgi-bin/man.cgi/OpenBSD-current/man8/sshd.8?query=sshd&sec=8) and [`dropbear`](http://linux.die.net/man/8/dropbear) on Arch Linux:

```
528-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I=R=S_]$ diff -y arch_sshd_deps.txt arch_dropbear_deps.txt
        /lib64/ld-linux-x86-64.so.2 (0x00007f95589a0000)      |         /lib64/ld-linux-x86-64.so.2 (0x00007ffaaff60000)
        libc.so.6 => /usr/lib/libc.so.6 (0x00007f9557440000)  |         libc.so.6 => /usr/lib/libc.so.6 (0x00007ffaaf560000)
        libcom_err.so.2 => /usr/lib/libcom_err.so.2 (0x00007f |         libcrypt.so.1 => /usr/lib/libcrypt.so.1 (0x00007ffaaf
        libcrypt.so.1 => /usr/lib/libcrypt.so.1 (0x00007f9557 |         libutil.so.1 => /usr/lib/libutil.so.1 (0x00007ffaafd5
        libcrypto.so.1.0.0 => /usr/lib/libcrypto.so.1.0.0 (0x |         libz.so.1 => /usr/lib/libz.so.1 (0x00007ffaafb40000)
        libdl.so.2 => /usr/lib/libdl.so.2 (0x00007f9557238000 |         linux-vdso.so.1 (0x00007fff45002000)
        libgssapi_krb5.so.2 => /usr/lib/libgssapi_krb5.so.2 ( <
        libk5crypto.so.3 => /usr/lib/libk5crypto.so.3 (0x0000 <
        libkeyutils.so.1 => /usr/lib/libkeyutils.so.1 (0x0000 <
        libkrb5.so.3 => /usr/lib/libkrb5.so.3 (0x00007f95577e <
        libkrb5support.so.0 => /usr/lib/libkrb5support.so.0 ( <
        libpam.so.0 => /usr/lib/libpam.so.0 (0x00007f95587900 <
        libpthread.so.0 => /usr/lib/libpthread.so.0 (0x00007f <
        libresolv.so.2 => /usr/lib/libresolv.so.2 (0x00007f95 <
        libutil.so.1 => /usr/lib/libutil.so.1 (0x00007f955817 <
        libz.so.1 => /usr/lib/libz.so.1 (0x00007f9557f58000)  <
        linux-vdso.so.1 (0x00007fff32c02000)                  <
```

One particular problem in this situation is that I do not want the SSH daemon executable to rely on shared object code, as it will likely be missing on the phone or there but not-quite-working.

In other words, I want a big, fat statically-linked binary that's entirely self-contained. And so I was delighted to find one such ready-made binary, complete with a how-to for setting up public key authentication (it's not *quite* the same as OpenSSH) on [Sven's blog](http://www.cri.ch/sven/doku.php/blog/running-dropbear-on-android).

I used the microSD slot on the phone to transfer the dropbear executables onto the phone and, [`cp(1)`](http://linux.die.net/man/1/cp) being conspicuously absent from the firmware, `toolbox`'s `dd(1)` to copy them from the card's to the read-write `/data` filesystem where proper \*nix file permissions could be set, unlike the card's FAT32 filesystem. I followed the steps on the page and was able to connect to the dropbear process.

There was a slight hurdle, however, with the call to `getusershell()` that dropbear [performs](https://github.com/mkj/dropbear/blob/master/svr-auth.c#L294) to validate the shell it would spawn for the user attempting to log in the event of a successful authentication.

The build of dropbear from that page has a patch applied to it that mocks the call to [`getpwnam(3)`](http://linux.die.net/man/3/getpwnam) to ensure that the user is always found and its login shell is hardcoded to `/system/xbin/sh`. This is great, but dropbear still attempts to open up `/etc/shells` to [check](https://github.com/mkj/dropbear/blob/master/compat.c#L236) that this is a registered login shell and, failing that, attempts to default to `/bin/sh`, then `/bin/csh`... neither of which exists on the phone.

I considered patching the dropbear source and recompiling it, but decided remounting `/system` read-write (`/etc` being symlinked to `/system/etc`) and echoing `/system/bin/sh` into `/system/etc/shells` was the more pragmatic approach, even though as a forensic exercise I really shouldn't touch a read-only file system. I'm not proud.

```
629-mboyer@marylou:~/Hacks/Nam-Phone_G40C/PYaffs [master:I±R=S+]$ ssh -v -i ../nam_id_rsa_openssh root@192.168.1.17
OpenSSH_6.7p1, OpenSSL 1.0.1j 15 Oct 2014
debug1: Reading configuration data /etc/ssh/ssh_config
debug1: Connecting to 192.168.1.17 [192.168.1.17] port 22.
debug1: Connection established.
debug1: key_load_public: No such file or directory
debug1: identity file ../nam_id_rsa_openssh type -1
debug1: key_load_public: No such file or directory
debug1: identity file ../nam_id_rsa_openssh-cert type -1
debug1: Enabling compatibility mode for protocol 2.0
debug1: Local version string SSH-2.0-OpenSSH_6.7
debug1: Remote protocol version 2.0, remote software version dropbear_0.52
debug1: no match: dropbear_0.52
debug1: SSH2_MSG_KEXINIT sent
debug1: SSH2_MSG_KEXINIT received
debug1: kex: server->client aes128-ctr hmac-sha1 none
debug1: kex: client->server aes128-ctr hmac-sha1 none
debug1: sending SSH2_MSG_KEXDH_INIT
debug1: expecting SSH2_MSG_KEXDH_REPLY
debug1: Server host key: RSA 0e:98:fa:4e:51:e6:5a:51:3e:cd:a5:69:1b:f5:36:54
debug1: Host '192.168.1.17' is known and matches the RSA host key.
debug1: Found key in /home/mboyer/.ssh/known_hosts:10
debug1: SSH2_MSG_NEWKEYS sent
debug1: expecting SSH2_MSG_NEWKEYS
debug1: SSH2_MSG_NEWKEYS received
debug1: Roaming not allowed by server
debug1: SSH2_MSG_SERVICE_REQUEST sent
debug1: SSH2_MSG_SERVICE_ACCEPT received
debug1: Authentications that can continue: publickey
debug1: Next authentication method: publickey
debug1: Trying private key: ../nam_id_rsa_openssh
debug1: Authentication succeeded (publickey).
Authenticated to 192.168.1.17 ([192.168.1.17]:22).
debug1: channel 0: new [client-session]
debug1: Entering interactive session.
[1007] Jun 01 19:07:17 lastlog_perform_login: Couldn't stat /var/log/lastlog: No such file or directory
[1007] Jun 01 19:07:17 lastlog_openseek: /var/log/lastlog is not a file or directory!
# id
id: not found
# set
HOME=/data/dropbear
IFS='
'
LOGNAME=root
OPTIND=1
PATH=/usr/bin:/bin
PS1='# '
PS2='> '
PS4='+ '
SHELL=/system/bin/sh
TERM=screen-256color
USER=root
_=id
# export PATH=/system/bin:/system/xbin
# id
uid=0(root) gid=0(root) groups=0(root)
#
```

And so finally I was able to connect to my phone from my regular Linux environment. If only all [drop bear](http://australianmuseum.net.au/Drop-Bear) encounters went so well!

![Dropbears!](http://fc03.deviantart.net/fs71/f/2011/317/2/5/woot_shirt___drop_bears_v2_by_fablefire-d4g4ssa.jpg)

> Dropbear illustration ©[fablefire](http://fablefire.deviantart.com/art/Woot-Shirt-Drop-Bears-v2-268962490)


# Archiving the FS

This is nice and way more comfortable but I still need a way to copy the whole filesystem over the network.

SCP and SFTP don't work because dropbear doesn't include the respective binaries that would be needed to make them work 

Soemthing Jan Pechanec's [post](https://blogs.oracle.com/janp/entry/how_the_scp_protocol_works)

I'll do this the old school way with tar and netcat.

Unfortunately, the phone's toolbox doesn't include them.

Busybox to the rescue! Link to zoobab github repo

Final netcat CLI

	# busybox tar -cv -f - --exclude='sys/*' --exclude='dev/*' --exclude='proc/*' / | busybox nc 192.168.1.10 9876
