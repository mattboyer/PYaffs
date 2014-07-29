---
layout: post
title: "Hacklog #3: Down in the dumps"
tags: spflashtool flash usb
---

# Down in the dumps

I mentioned in the first post that tools exist that can be used to write/read flash for this family of devices. The most legit-looking one I found is called SPFlashTool and is available on [this site](http://mtk2000.ucoz.ru/), which looks somewhat affiliated to MediaTek.

http://forum.xda-developers.com/showthread.php?t=1982587

Something about "scatter"

There was a dialog where I entered an offset and a size - that should tie in with the last section


{% highlight bash %}
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

{% endhighlight %}

{% highlight bash %}
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
{% endhighlight %}


Need to use attach-device qemu_test_domain /home/mboyer/03_dev.xml --current



Workflow:

VM does not have any USB devices
Phone not connected

Hold phone vol down button down and connect phone

Dev with id 0003 appears in the output of lsusb

Attach it to the VM with xml

Install driver onto the VM
(show output of usbview)

Click on read back in spflash tool

A red progress bar is shown and 120Kb of data are downloaded into the phone

A device with id 2001 appears

Detach the 03 device
Attach the 2001 device to the VM

Install driver for it (may need to hack some INF files)


lsusb with 03 device:
{% highlight bash %}
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
{% endhighlight %}


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

