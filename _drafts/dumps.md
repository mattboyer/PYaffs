---
layout: post
title: "Hacklog #3: Down in the dumps"
tags: spflashtool flash usb libvirt pass-through
---

# Down in the dumps

This one's a big post. Getting the dumps was a process of trial and error the first time around and I made the mistake of not documenting what worked and what didn't, meaning I had to go through all that pain a second time to write this post. There's a lesson in there, kids. Always log when you hack.

## Tools

I mentioned in the first post that tools exist that can be used to write/read flash for this family of devices. The most legit-looking one I found is called *Smart Phone Flash Tool* (or SPFlashTool in some filenames) and is available on [this Russian-language site](http://mtk2000.ucoz.ru/), which looks somewhat affiliated to MediaTek.

From that same site, I grabbed a zip archive containing drivers for MediaTek SoC's in the 65xx series.

This is what SPFlashTool looks like:

!["SPFlashTool main GUI window"]({{ site.baseurl }}/images/SP_Flash_1.png)

!["SPFlashTool about dialog"]({{ site.baseurl }}/images/SP_Flash_2.png)

The tool's "Download" tab is concerned with getting flash images *into the phone* whereas getting flash dumps *out* is achieved through the "Read back" tab.

## Connectivity with the phone

When the phone is up and running Android, it reports itself as a `HTC (High Tech Computer Corp.) Android Phone` with the USB Vendor/Product ID pair `0bb4:0c03`. This is the USB device that the Android SDK tools talk to. Getting the dumps is done through a different process that involves a good deal of messing around with USB devices.

If the phone is connected while it is powered off, then a USB device with the VID/PID pair `0e8d:2000` and the description string `MediaTek Inc. MT65xx Preloader`. This device is transient and is seen for a period time shorter than 3 seconds. It's a blink-and-you-miss-it kinda deal:

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

If, on the other hand, the phone is connected while it is powered off *and the volume down key is held down*, then a device with VID/PID `0e8d:0003` (`MediaTek Inc. MT6227 phone`) is seen on the USB host and remains active on the USB bus. That means it can actually be used with the right tool to get something to/from the phone:

	287-mboyer@marylou:~ [master:I±R=]$ lsusb
	Bus 002 Device 003: ID 04f2:b2ea Chicony Electronics Co., Ltd Integrated Camera [ThinkPad]
	Bus 002 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
	Bus 008 Device 002: ID 04ca:2007 Lite-On Technology Corp. 
	Bus 008 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
	Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
	Bus 007 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
	Bus 006 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
	Bus 005 Device 002: ID 045e:0737 Microsoft Corp. Compact Optical Mouse 500
	Bus 005 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
	Bus 004 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
	Bus 003 Device 008: ID 0e8d:0003 MediaTek Inc. MT6227 phone
	Bus 003 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub

Let's see what the INF files in the driver archive have that would match either device:

	132-mboyer@marylou:~/tmp/Win_Stuff [master:I±R=]$ find . -type f -name '*.inf' -exec egrep -C2 -i '0e8d.*2000' {} \; -print
	%MTK_COM%=Reader,USB\Vid_0e8d&Pid_0023&MI_00
	%MTK_CAT%=Reader,USB\Vid_0e8d&Pid_0023&MI_02
	%MTK_PRELOADER%=Reader, USB\Vid_0e8d&Pid_2000
	%MTK_SP_DA%=Reader, USB\Vid_0e8d&Pid_2001

	./drivers/6513&6573&6575/SP_Flash_Tool_v2.1134.00/SP_Flash_Tool_v2.1134.00/new usb driver/2K_XP_COM/usb2ser_2kXP.inf
	%DEV_COM_APP%=DriverInstall,USB\VID_0E8d&PID_00A2&MI_01

	%VCOM_PRELOADER%=DriverInstall,USB\VID_0E8D&PID_2000

	[DriverInstall.ntx86]
	./drivers/6513&6573&6575/Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/WinXP_Driver/usb2ser_xp.inf
	%DEV_COM_APP%=DriverInstall,USB\VID_0E8d&PID_00A2&MI_01

	%VCOM_PRELOADER%=DriverInstall,USB\VID_0E8D&PID_2000

	[DriverInstall.NTamd64]
	./drivers/6513&6573&6575/Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Vista64_Driver/usb2ser_V64.inf
	%DEV_COM_APP%=DriverInstall,USB\VID_0E8d&PID_00A2&MI_01

	%VCOM_PRELOADER%=DriverInstall,USB\VID_0E8D&PID_2000

	[DriverInstall.ntx86]
	./drivers/6513&6573&6575/Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Win732_Driver/usb2ser_Win732.inf
	%DEV_COM_APP%=DriverInstall,USB\VID_0E8d&PID_00A2&MI_01

	%VCOM_PRELOADER%=DriverInstall,USB\VID_0E8D&PID_2000

	[DriverInstall.ntx86]
	./drivers/6513&6573&6575/Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Vista32_Driver/usb2ser_V32.inf
	%DEV_COM_APP%=DriverInstall,USB\VID_0E8d&PID_00A2&MI_01

	%VCOM_PRELOADER%=DriverInstall,USB\VID_0E8D&PID_2000


	./drivers/6513&6573&6575/Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Win764_Driver/usb2ser_Win764.inf
	; BootRom & Preloader VCOM
	%VCOM_BOOTROM%=DriverInstall, USB\Vid_0e8d&Pid_0003
	%VCOM_PRELOADER%=DriverInstall, USB\Vid_0e8d&Pid_2000

	[DeviceList.NTamd64]
	--
	; BootRom & Preloader VCOM
	%VCOM_BOOTROM%=DriverInstall, USB\Vid_0e8d&Pid_0003
	%VCOM_PRELOADER%=DriverInstall, USB\Vid_0e8d&Pid_2000

	;------------------------------------------------------------------------------
	./drivers/6513&6573&6575/Driver_USB/Driver - USB VCOM Driver (binary)/mtk_sp_usb2ser.inf

That's a whole bunch of matches. Let's have a look at the driver that matches my VM's OS best:
{% highlight ini %}
[Version]
Signature="$Windows NT$"
Class=Ports
ClassGuid={4D36E978-E325-11CE-BFC1-08002BE10318}
Provider=%MEDIATEK%
DriverVer=04/29/2011,2.0.1118.0

[Manufacturer]
%MEDIATEK%=DeviceList, NTamd64

[DestinationDirs]
DefaultDestDir=12

;------------------------------------------------------------------------------
;  Vista/Win7-64bit Sections
;------------------------------------------------------------------------------

[DriverInstall.NTamd64]
include=mdmcpq.inf
CopyFiles=DriverCopyFiles.NTamd64
AddReg=DriverInstall.NTamd64.AddReg

[DriverCopyFiles.NTamd64]
USBSER.sys,,,0x20

[DriverInstall.NTamd64.AddReg]
HKR,,DevLoader,,*ntkern
HKR,,NTMPDriver,,USBSER.sys
HKR,,EnumPropPages32,,"MsPorts.dll,SerialPortPropPageProvider"

[DriverInstall.NTamd64.Services]
AddService=usbser, 0x00000002, DriverService.NTamd64

[DriverService.NTamd64]
DisplayName=%SERVICE%
ServiceType=1
StartType=3
ErrorControl=1
ServiceBinary=%12%\USBSER.sys


;------------------------------------------------------------------------------
;  Vendor and Product ID Definitions
;------------------------------------------------------------------------------

[DeviceList]
%GADGET%=DriverInstall, USB\VID_0BB4&PID_0005&MI_02

; BootRom & Preloader VCOM
%VCOM_BOOTROM%=DriverInstall, USB\Vid_0e8d&Pid_0003
%VCOM_PRELOADER%=DriverInstall, USB\Vid_0e8d&Pid_2000

[DeviceList.NTamd64]
%GADGET%=DriverInstall, USB\VID_0BB4&PID_0005&MI_02

; BootRom & Preloader VCOM
%VCOM_BOOTROM%=DriverInstall, USB\Vid_0e8d&Pid_0003
%VCOM_PRELOADER%=DriverInstall, USB\Vid_0e8d&Pid_2000

;------------------------------------------------------------------------------
;  String Definitions
;------------------------------------------------------------------------------

[Strings]
MEDIATEK            = "MediaTek Inc."
GADGET              = "Gadget Serial"
SERVICE             = "USB RS-232 Emulation Driver"
VCOM_BOOTROM        = "MediaTek USB Port"
VCOM_PRELOADER      = "MediaTek PreLoader USB VCOM (Android)"
{% endhighlight %}

We can infer from that that both devices act as serial ports, the former (`0e8d:2000`) being exposed by the preloader (presumably a piece of software involved in the very early stages of the boot process) and the latter (`0e8d:0003`) by the "Boot ROM", which *might* be the software that implements the offline behaviour of the phone (ie. display the battery graphic when the phone is charging, listen for events on the power button and the USB port). That's an educated guess, of course, and I may yet be very wrong.

## Connecting the phone to the VM

I want to connect the phone to my work VM as the `0e8d:0003` USB device. Since this is a transient device (it appears only when I physically connect the phone), I'll need to simulate attaching the device to the VM using Qemu and libvirt's support for hot-plugging pass-through devices. I prepared a XML description of the device:

{% highlight xml %}
<hostdev mode='subsystem' type='usb' managed='yes'>
	<source>
		<vendor id='0x0e8d'/>
		<product id='0x0003'/>
	</source>
	<address type='usb' bus='0' port='1'/>
</hostdev>
{% endhighlight %}

The trick here is to mandate the USB port on which the device will appear on the guest, else Windows XP's driver detection routine will kick in every time the device is attached. That device can be dynamically attached to a running VM with:

	364-mboyer@marylou:~/MT_Screenshots [master:I±R=]$ virsh 
	Welcome to virsh, the virtualization interactive terminal.

	Type:  'help' for help with commands
	       'quit' to quit

	virsh # attach-device qemu_test_domain /home/mboyer/03_dev.xml --current

And hey presto! it shows up in the output of usbview:

!["Boot ROM device seen in usbview"]({{ site.baseurl }}/images/03_device_usbview.png)

I installed the driver described in the above INF file for that device:

!["Boot ROM device driver installation"]({{ site.baseurl }}/images/03_device_driver.png)


# Using SPFlashTool

## Something about scatter

Populate the Flash partitions' start offsets and sizes derived in the last blog in the 'read back' tab of SPFlashTool

To Be Written: mention the need to use the 'full speed' option (ie. the one that doesn't trigger the 2001 device)

Click on read back in spflash tool

A red progress bar is shown and 120Kb of data are downloaded into the phone

!["Boot ROM device driver installation"]({{ site.baseurl }}/images/DA_download.png)


Mention that if the other option is chosen, then the 03 device disappears and is replaced by another device (2001) that allows faster but less reliable transfers

	289-mboyer@marylou:~ [master:I±R=]$ lsusb
	Bus 002 Device 003: ID 04f2:b2ea Chicony Electronics Co., Ltd Integrated Camera [ThinkPad]
	Bus 002 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
	Bus 008 Device 002: ID 04ca:2007 Lite-On Technology Corp. 
	Bus 008 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
	Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
	Bus 007 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
	Bus 006 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
	Bus 005 Device 002: ID 045e:0737 Microsoft Corp. Compact Optical Mouse 500
	Bus 005 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
	Bus 004 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
	Bus 003 Device 013: ID 0e8d:2001 MediaTek Inc. 
	Bus 003 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub


In the end, I got a beautiful dump of the MTD partition that backs my phone's `/system` filesystem:

	358-mboyer@marylou:~ [master:I±R=]$ stat system.img 
	  File: ‘system.img’
	  Size: 318996480       Blocks: 623048     IO Block: 4096   regular file
	Device: fe01h/65025d    Inode: 793895      Links: 1
	Access: (0644/-rw-r--r--)  Uid: ( 1000/  mboyer)   Gid: ( 1000/  mboyer)
	Access: 2014-07-30 00:32:08.793372357 +0100
	Modify: 2014-07-30 00:32:02.013372488 +0100
	Change: 2014-07-30 00:32:02.013372488 +0100
	 Birth: -

