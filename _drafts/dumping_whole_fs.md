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

The ``/system`` dump I extracted includes a bunch of interesting CLI executables, most of which are implemented by an all-in-one binary, ``/system/bin/toolbox``.

- Insert relevant files

Unfortunately, while there are some power tools in there I couldn't find a SSH daemon in the original firmware. Using the [OpenSSH](http://www.openssh.com/) implementation of the [Secure SHell protocol](http://datatracker.ietf.org/wg/secsh/documents/) would be possible

- Explain why I need statically-linked binaries

I first need a way to connect to the Linux OS running on the phone from another system. There's no sshd in the firmware so this is a job for [dropbear](https://matt.ucc.asn.au/dropbear/dropbear.html)

!["Dropbears!"](http://fc03.deviantart.net/fs71/f/2011/317/2/5/woot_shirt___drop_bears_v2_by_fablefire-d4g4ssa.jpg)

Dropbear illustration © [fablefire](http://fablefire.deviantart.com/art/Woot-Shirt-Drop-Bears-v2-268962490)

(deviantart link), dropbear link

Steps from sven's blog

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

This is nice and way more comfortable but I still need a way to copy the whole filesystem over the network.

# Archiving the FS

SCP and SFTP don't work because dropbear doesn't include the respective binaries that would be needed to make them work (link to Jan's blog)

I'll do this the old school way with tar and netcat.

Unfortunately, the phone's toolbox doesn't include them.

Busybox to the rescue! Link to zoobab github repo

Final netcat CLI

	# busybox tar -cv -f - --exclude='sys/*' --exclude='dev/*' --exclude='proc/*' / | busybox nc 192.168.1.10 9876
