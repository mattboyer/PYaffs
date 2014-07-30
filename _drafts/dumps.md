---
layout: post
title: "Hacklog #3: Dumping the Flash ROM"
tags: spflashtool flash usb libvirt pass-through
---

# Down(load)in' in the dumps

This one's a big post. Getting the dumps was a process of trial and error the first time around and I made the mistake of not documenting what worked and what didn't, meaning I had to go through all that pain a second time to write this post.

There's a lesson in there, kids. Always log when you hack.

## Tools

I mentioned in the first post that tools exist that can be used to write/read flash for this family of devices. The most legit-looking one I found is called *Smart Phone Flash Tool* (or SPFlashTool in some filenames) and is available from [this Russian-language site](http://mtk2000.ucoz.ru/). The site looks a bit dodgy in a back alley phone repair shop kinda way, but it also looks like it has some kind of legit affiliation to MediaTek. Anyway, I also grabbed a zip archive containing drivers for MediaTek SoC's in the 65xx series from the site.

This is what SPFlashTool looks like:

!["SPFlashTool main GUI window"]({{ site.baseurl }}/images/SP_Flash_1.png)

!["SPFlashTool about dialog"]({{ site.baseurl }}/images/SP_Flash_2.png)

The tool's "Download" tab is concerned with getting flash images *into the phone* whereas getting flash dumps *out* is achieved through the "Read back" tab.

## Connectivity with the phone

When the phone is up and running Android, it reports itself as a `HTC (High Tech Computer Corp.) Android Phone` with the USB Vendor/Product ID pair `0bb4:0c03`. This is the USB device that the Android SDK tools talk to.

Getting the dumps is done through a different process that involves a good deal of messing around with USB devices.

If the phone is connected while it is powered off, then a USB device with the VID/PID pair `0e8d:2000` and the description string `MediaTek Inc. MT65xx Preloader` appears on the USB root hub. This device is transient and is seen for a period time shorter than 3 seconds. It's a blink-and-you-miss-it deal:

	364-mboyer@marylou:~ [master:I±R=]$ lsusb | grep -i mediatek
	Bus 001 Device 002: ID 0e8d:2000 MediaTek Inc. MT65xx Preloader


If, on the other hand, the phone is connected while it is powered off *and the Volume Down key is held down*, then a device with VID/PID `0e8d:0003` (`MediaTek Inc. MT6227 phone`) is seen on the USB root hub and remains active as long as the phone is plugged in and therefore can actually be used to get something to/from the phone:

	365-mboyer@marylou:~ [master:I±R=]$ lsusb | grep -i mediatek
	Bus 001 Device 003: ID 0e8d:0003 MediaTek Inc. MT6227 phone

Let's see what the INF files in the driver archive have that would match that device:

	376-mboyer@marylou:~/tmp/Win_Stuff/drivers/6513&6573&6575 [master:I±R=]$ find . -type f -name '*.inf' -exec egrep -qi '0e8d.*0003' {} \; -print
	./SP_Flash_Tool_v2.1134.00/SP_Flash_Tool_v2.1134.00/new usb driver/2K_XP_COM/usb2ser_2kXP.inf
	./Driver_USB/Driver - USB Tethering Driver (binary)/usbser/Win7/usb2ser_Win764.inf
	./Driver_USB/Driver - USB Tethering Driver (binary)/usbser/Win7/usb2ser_Win7.inf
	./Driver_USB/Driver - USB Tethering Driver (binary)/usbser/2K_XP_COM/usb2ser_XP64.inf
	./Driver_USB/Driver - USB Tethering Driver (binary)/usbser/2K_XP_COM/usb2ser_2kXP.inf
	./Driver_USB/Driver - USB Tethering Driver (binary)/usbser/Vista/usb2ser_Vista.inf
	./Driver_USB/Driver - USB Tethering Driver (binary)/usbser/Vista/usb2ser_Vista64.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/MS_USB_Driver_exe_v1.1032.1/USB_Driver_exe_v1.1032.1/v1.1032.1/Win7/usb2ser_Win764.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/MS_USB_Driver_exe_v1.1032.1/USB_Driver_exe_v1.1032.1/v1.1032.1/Win7/usb2ser_Win7.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/MS_USB_Driver_exe_v1.1032.1/USB_Driver_exe_v1.1032.1/v1.1032.1/2K_XP_COM/usb2ser_XP64.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/MS_USB_Driver_exe_v1.1032.1/USB_Driver_exe_v1.1032.1/v1.1032.1/2K_XP_COM/usb2ser_2kXP.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/MS_USB_Driver_exe_v1.1032.1/USB_Driver_exe_v1.1032.1/v1.1032.1/Vista/usb2ser_Vista.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/MS_USB_Driver_exe_v1.1032.1/USB_Driver_exe_v1.1032.1/v1.1032.1/Vista/usb2ser_Vista64.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ModemPortDriver/WinXP_Driver/modem_xp.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ModemPortDriver/Vista64_Driver/modem_v64.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ModemPortDriver/Win732_Driver/modem_w732.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ModemPortDriver/Vista32_Driver/modem_v32.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ModemPortDriver/Win764_Driver/modem_w764.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/WinXP_Driver/usb2ser_xp.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Vista64_Driver/usb2ser_V64.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Win732_Driver/usb2ser_Win732.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Vista32_Driver/usb2ser_V32.inf
	./Driver_USB/Driver - USB Cable Driver (binary)/v1.1121.0/ComPortDriver/Win764_Driver/usb2ser_Win764.inf
	./Driver_USB/Driver - USB VCOM Driver (binary)/mtk_sp_usb2ser.inf

That's a lot of INF files! I arbitrarily chose to have a look at what's inside the last one:

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

We can infer from the contents of that file that both devices act as serial ports, the former (`0e8d:2000`) being exposed by the preloader - presumably a piece of software involved in the very early stages of the boot process - and the latter (`0e8d:0003`) by the "Boot ROM", which *might* be the software that implements the offline behaviour of the phone (ie. display the battery gauge when the phone is charging, listen for events on the power button and the USB port). These are educated guesses, of course, and nothing more.

## Connecting the phone to the VM

I wanted to connect the phone to my work VM as the `0e8d:0003` USB device. Since this is a transient device (it appears only when I physically connect the phone), I'll need to simulate attaching the device to the VM using QEmu and libvirt's support for hot-plugging pass-through devices. I prepared a XML description of the device:

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

	364-mboyer@marylou:~ [master:I±R=]$ virsh 
	Welcome to virsh, the virtualization interactive terminal.

	Type:  'help' for help with commands
	       'quit' to quit

	virsh # attach-device qemu_test_domain /home/mboyer/03_dev.xml --current

And hey presto! it shows up in the output of usbview on the guest:

!["Boot ROM device seen in usbview"]({{ site.baseurl }}/images/03_device_usbview.png)

I installed the driver described in the above INF file for that device:

!["Boot ROM device driver installation"]({{ site.baseurl }}/images/03_device_driver.png)


# Dumping hack flash (*it's a gas gas gas!*)

Since I've finally established some sort of serial-based connectivity between my VM and the Nam-Phone's pre-Android software, it's time to try out the *Smart Phone Flash Tool*.

The "Read back" tab of the GUI presents the user with a grid-like widget where every row represents a segment of Flash ROM to upload from the phone. There are four parameter for each dump: name of the output file, read flags, start offset and dump size.

And I just happen to have these last two pieces of information from the [last post]({{site.baseurl}}{% post_url 2014-07-21-Hacklog#2 %})! Pretty convenient, huh?

!["SPFlashTool \"Read back\" GUI"]({{ site.baseurl }}/images/read_back_tab.png)

!["SPFlashTool \"Read back\" dialog"]({{ site.baseurl }}/images/read_back_dialog.png)

Time to click the "Read back" icon and let the magic happen, eh?

!["Oh crap"]({{ site.baseurl }}/images/scatter.png)

## Well, shit.

After a fair amount of head-scratching, I figured out that this "scatter file" is really a text-based map of the Flash partitions (how and where they are *scattered* across the Flash, as it were).

Now, I've no idea why we need to import that information from a file considering we're manually entering the start offset and length of the dump to download from the phone, but the tool was stubborn. The format for these "scatter files" isn't documented anywhere I could find either, so I had to hunt for examples.

Starting from a sample "scatter file" I found attached to a forum post, I managed to craft a minimal "scatter file" that would placate SPFlashTool without introducing any extraneous data in the process. Here it is:

	411-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ cat min_scatter.txt
	PRELOADER 0x0
	{
	}

	412-mboyer@marylou:~/Hacks/Nam-Phone_G40C [master:I±R=]$ xxd -g1  min_scatter.txt 
	0000000: 50 52 45 4c 4f 41 44 45 52 20 30 78 30 0a 7b 0a  PRELOADER 0x0.{.
	0000010: 7d 0a 

It's worth noting that SPFlashTool borks if the newlines in the scatter file follow the DOS convention (ie. `0D 0A` instead of just `0A`)

## Here we go again

With the "scatter file" loaded, I can finally trigger the download of the `system` partition dump. SPFlashTool handles this as a two-part process:

- First, a red progress bar is shown and ~120Kb of data are downloaded into the phone

  !["Boot ROM device driver installation"]({{ site.baseurl }}/images/DA_download.png)

  I believe that these 120Kb of data are what the tool refers to as the "DA" or Download Agent. Based on the name and size, it's likely to be a bit of code loaded into the RAM that allows access to the Flash device and handles serial communication with SPFlashTool.

- Then the actual download begins. Transfer rates shown by SPFlashTool seem to hover around ~180Kbps for me using the 'Full Speed' option, ie. connecting to the phone's `0e8d:0003` device over USB1.1.

  !["Flash ROM dump download"]({{ site.baseurl }}/images/full_speed_dump_download.png)

At long last, I have a dump of the `system` partition!

!["Flash ROM dump successful"]({{ site.baseurl }}/images/full_speed_dump_download_successful.png)

	358-mboyer@marylou:~ [master:I±R=]$ stat system.img 
	  File: ‘system.img’
	  Size: 318996480       Blocks: 623048     IO Block: 4096   regular file
	Device: fe01h/65025d    Inode: 793895      Links: 1
	Access: (0644/-rw-r--r--)  Uid: ( 1000/  mboyer)   Gid: ( 1000/  mboyer)
	Access: 2014-07-30 00:32:08.793372357 +0100
	Modify: 2014-07-30 00:32:02.013372488 +0100
	Change: 2014-07-30 00:32:02.013372488 +0100
	 Birth: -

Yay!

## Further considerations

As I alluded to above, there is a config option in SPFlashTool that lets the user select whether they want to communication between the tool and DA to occur over USB 1.1 or USB2 ("High speed" mode). When this option is selected, the `0e8d:0003` device disappears from the host's and guest's USB root hub after the Download Agent has been loaded and is replaced by yet another USB device, this time with VID/PID `0e8d:2001`:

	289-mboyer@marylou:~ [master:I±R=]$ lsusb | grep -i mediatek
	Bus 003 Device 013: ID 0e8d:2001 MediaTek Inc.

I've tried to configure QEmu pass-through to detach `0e8d:0003` from the guest and connect the new `0e8d:2001` device when it appears. I had to hack the INF file above to let Windows on the VM know that it should treat this device in a similar fashion to the other devices in the INF.

That actually *did work*, however transfers were very unreliable: SPFlashTool would frequently abort the dump transfer for no clear reason. Slow and steady does it, sometimes.

Also, one of the cool things with using USB pass-through, and part of the reason I went through all this pain to get a dump I already had, is that one can use [`tshark(1)`](http://www.wireshark.org/docs/man-pages/tshark.html) and Linux's [`usbmon`](https://www.kernel.org/doc/Documentation/usb/usbmon.txt) module to dump USB traffic to and from the guest. This is of great interest to me, since I would ideally like to replicate SPFlashTool's functionality in a native Linux tool.
