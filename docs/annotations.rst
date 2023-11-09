.. _annotations-chapter:

=================
Crash Annotations
=================

.. contents::
   :local:


Overview
========

A crash report contains a set of :term:`crash annotations <crash annotation>`.

In a crash report, all values are strings, but they can be decoded as a variety
of data types like strings, integers, floats, and JSON-encoded structures.

For example, a crash report may contain the following annotations:

Example::

    ProductName=Firefox

Example::

    Version=115.3.0

Example::

    BuildID=20231004091611

Example::

    CPUMicrocodeVersion=0xb4

Example (wrapped)::

    MozCrashReason=Shutdown hanging at step AppShutdownConfirmed. Something is blocking th
    e main-thread.

Example (wrapped)::

    ModuleSignatureInfo={"ESET, spol. s r.o.":["eplgFirefox.dll"],"Microsoft Corporation":
    ["VCRUNTIME140_1.dll","msvcp140.dll","VCRUNTIME140.dll"],"Microsoft Windows":["winrnr.
    dll","pnrpnsp.dll","Windows.Globalization.dll","NapiNSP.dll","DWrite.dll","ondemandcon
    nroutehelper.dll","twinapi.dll","wininet.dll","webauthn.dll","wscapi.dll","winmm.dll",
    "FWPUCLNT.DLL","dbgcore.dll","urlmon.dll","srvcli.dll","rasadhlp.dll","winhttp.dll","i
    ertutil.dll","Windows.UI.Immersive.dll","ktmw32.dll","dhcpcsvc.dll","dhcpcsvc6.DLL","n
    pmproxy.dll","winnsi.dll","BCP47mrm.dll","TextInputFramework.dll","InputHost.dll","Win
    dowManagementAPI.dll","Windows.UI.dll","Bcp47Langs.dll","version.dll","wshbth.dll","ms
    cms.dll","dcomp.dll","wsock32.dll","netprofm.dll","nlaapi.dll","twinapi.appcore.dll","
    WinTypes.dll","CoreMessaging.dll","CoreUIComponents.dll","ColorAdapterClient.dll","pro
    psys.dll","uxtheme.dll","dwmapi.dll","windows.storage.dll","gpapi.dll","dxgi.dll","dbg
    help.dll","wtsapi32.dll","kernel.appcore.dll","rsaenh.dll","ntmarta.dll","winsta.dll",
    "IPHLPAPI.DLL","dnsapi.dll","netutils.dll","mswsock.dll","cryptsp.dll","cryptbase.dll"
    ,"wldp.dll","ntasn1.dll","ncrypt.dll","msasn1.dll","devobj.dll","sspicli.dll","userenv
    .dll","profapi.dll","cfgmgr32.dll","bcryptPrimitives.dll","crypt32.dll","msvcp_win.dll
    ","KERNELBASE.dll","win32u.dll","gdi32full.dll","bcrypt.dll","wintrust.dll","ucrtbase.
    dll","imm32.dll","sechost.dll","oleaut32.dll","msctf.dll","ole32.dll","advapi32.dll","
    ws2_32.dll","clbcatq.dll","kernel32.dll","shlwapi.dll","nsi.dll","setupapi.dll","psapi
    .dll","combase.dll","msvcrt.dll","user32.dll","shell32.dll","SHCore.dll","gdi32.dll","
    rpcrt4.dll","ntdll.dll"],"Mozilla Corporation":["firefox.exe","xul.dll","nss3.dll","fr
    eebl3.dll","osclientcerts.dll","nssckbi.dll","mozglue.dll","softokn3.dll","lgpllibs.dl
    l"]}


Crash annotations for all Mozilla products are documented in
`CrashAnnotations.yaml`_.

.. _CrashAnnotations.yaml: https://hg.mozilla.org/mozilla-central/file/tip/toolkit/crashreporter/CrashAnnotations.yaml
