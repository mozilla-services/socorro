========
Glossary
========

.. glossary::
   :sorted:

   breakpad
       Breakpad is a set of client and server components that implement a
       crash reporting system.

       Mozilla currently uses a heavily patched Breakpad library.

       Mozilla is working on replacing Breakpad and other tools with new
       ones written in Rust.

       .. seealso::

          `Breakpad <https://chromium.googlesource.com/breakpad/breakpad/>`__
              Breakpad project code and documentation.

          `Mozilla's patched Breakpad <https://searchfox.org/mozilla-central/source/toolkit/crashreporter>`__


   crash annotation
       A crash annotation is a key/value pair with some bit of information.

       In a crash report, all values are strings, but they can be decoded as a
       variety of data types like strings, integers, floats, and JSON-encoded
       structures.

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

       .. seealso::

          `CrashAnnotations.yaml <https://searchfox.org/mozilla-central/source/toolkit/crashreporter/CrashAnnotations.yaml>`__
              Available crash annotations.

          `Socorro crash annotations schema <https://github.com/mozilla-services/socorro/blob/main/socorro/schemas/raw_crash.schema.yaml>`__
              Socorro schema for supported crash annotations including
              documentation, access controls, links to data reviews, and links
              to relevant bugs. This information can be seen in the `Crash
              Reporting Data Dictionary
              <https://crash-stats.mozilla.org/documentation/datadictionary/>`__.


   crash id
   uuid
   ooid
       A unique identifier for the :term:`crash report`. The collector
       generates the crash id and returns it to the :term:`crash reporter` in
       the HTTP response. The :term:`crash reporter` may keep it so that users
       have a list of :term:`crash reports <crash report>` they submitted with
       links to the the crash report on
       `Crash Stats <https://crash-stats.mozilla.org>`__.

       Crash ids look like this::

           de1bb258-cbbf-4589-a673-34f800160918
                                        ^^^^^^^
                                        ||____|
                                        |  yymmdd
                                        |
                                        throttle result

       Historically, Antenna used the throttle result to encode the throttle
       result so that we knew which crash reports were collected and accepted
       for processing and which ones were accepted and stored, but not accepted
       for processing. Antenna no longer accepts crash reports for storing, but
       not for processing, so this character is now always ``0``.

       Because of this structure, you can look at the last 6 characters and
       know when the crash report was collected.

       The crash id is also referred to as "uuid". The collector stores the
       crash id in the "uuid" key in the raw crash.

       (Deprecated) The crash id also used to be referred to as "ooid", but
       that term is deprecated and we should remove its usage everywhere.

       .. seealso::

          `Collector-added fields <https://antenna.readthedocs.io/en/latest/overview.html#collector-added-fields>`__
              List of fields the collector adds when accepting a crash report
              which includes "uuid".

          `Antenna spec v1 (2017) <https://antenna.readthedocs.io/en/latest/spec_v1.html#crash-ids>`__
              Original specification for the Antenna rewrite of the Socorro
              collector which includes a section on crash id structure.


   crash report
       A crash report consists of :term:`crash annotations <crash annotation>`
       and :term:`minidumps <minidump>`. It is the data packet that is sent by
       the :term:`crash reporter`, accepted by the collector, and processed by the
       processor.

       .. seealso::

          :ref:`crash-report-spec-chapter`
              Specification covering the structure of a crash report.


   crash reporter
       When a product crashes, the crash reporter kicks in, captures information
       about the state of the crashed process, product, and system, and assembles
       a :term:`crash report`.

       For :term:`Breakpad`-style crash reporters, the :term:`crash report`
       consists of :term:`crash annotations <crash annotation>` and zero or
       more :term:`minidumps <minidump>`.

       See :ref:`crash-report-spec-chapter` for the structure of a :term:`crash
       report` and how it's submitted.

       .. seealso::

          `Firefox crash reporter <https://searchfox.org/mozilla-central/source/toolkit/crashreporter>`__
              Code for the Firefox crash reporter.

          `Fenix crash reporter <https://github.com/mozilla-mobile/firefox-android/tree/main/android-components/components/lib/crash>`__
              Code for the Fenix crash reporter.


   crash signature
       The Socorro processor generates a crash signature for every crash report.

       Crash signatures help us group similar crashes glossing over
       differences in operating system versions, platforms, architectures,
       drivers, video cards, web sites, etc.

       Roughly, a signature consists of some flags followed by "interesting"
       symbols from the stack.

       Examples of signatures::

           OOM | small

           shutdownhang | nsThreadManager::SpinEventLoopUntilInternal

           mozilla::dom::ServiceWorkerRegistrar::GetShutdownPhase

           <style::stylesheets::rules_iterator::RulesIterator<C> as core::iter::traits::iterator::Iterator>::next

       .. seealso::

          :ref:`signaturegeneration-chapter`
              Documentation on Socorro's signature generation.


   dump
   minidump
       A minidump is a file format for storing information about a crashed
       process. It contains CPU information, register contents, stacks for
       the crashed thread and other threads, some interesting parts of the
       heap, list of loaded modules, list of unloaded modules, etc.

       Minidumps are smaller than core dumps which makes them handy for
       crash reporting.

       Minidumps are created and manipulated using the Breakpad library
       and the rust-minidump tools.

       .. seealso::

          `Minidump Files (Microsoft) <https://learn.microsoft.com/en-us/windows/win32/debug/minidump-files>`__
              Documentation on minidump file format.

          `rust-minidump <https://github.com/rust-minidump/rust-minidump>`__
              Type definitions, parsing, and analysis for the minidump file format.


   processed crash
       The Socorro processor takes crash annotations and minidumps, runs them
       through the processing pipeline, and generates a processed crash.

       The processed crash contains normalized and validated data derived
       from the original crash report.

       .. seealso::

          `Socorro processed crash schema <https://github.com/mozilla-services/socorro/blob/main/socorro/schemas/processed_crash.schema.yaml>`__
              Socorro processed crash schema including descriptions, access
              controls, source annotations (when appropriate), and other
              things. This information can be seen in the `Crash Reporting Data
              Dictionary
              <https://crash-stats.mozilla.org/documentation/datadictionary/>`__.


   protected data
       Socorro categorizes crash report data in two ways:

       1. public data
       2. protected data

       Public data is anything in Category 1 (technical data) and Category 2
       (interaction data).

       Protected data is anything more sensitive than that.

       By default, all data in the raw and processed crash is considered
       protected. In order for it to be marked as public, we require a data
       review and for it to be explicitly marked as public in the relevant
       schema.

       .. seealso::

          `Socorro protected data access policy <https://crash-stats.mozilla.org/documentation/protected_data_access/>`__
              Socorro's protected data access policy which covers who is
              allowed access to the data, what you can do with it, and how to
              get protected data access.

          `Data collection categories <https://wiki.mozilla.org/Data_Collection#Data_Collection_Categories>`__
              Definitions of data collection categories.


   raw crash
       The Socorro collector parses the HTTP POST payload into a set of crash
       annotations and minidumps. It collects the crash annotations along with
       some metadata generated at collection in a raw crash structure. It
       saves this to AWS S3.

       The Socorro processor takes the raw crash and minidumps and passes them
       through the processing pipeline to generate a processed crash.

       The collector tries to save the crash annotation data in the raw crash
       as it received it. There are some exceptions:

       1. Some crash annotations are no longer allowed to be collected. The
          collector will drop these before creating the raw crash. For example,
          we no longer collect the ``Email`` crash annotation.

       2. Annotations that raise some kind of parse error are dropped.

       When this happens, a note will be added to the "collector notes" which
       can be seen in the *Debug* tab of the report view in Crash Stats.

       .. seealso::

          `Socorro crash annotations schema <https://github.com/mozilla-services/socorro/blob/main/socorro/schemas/raw_crash.schema.yaml>`__
              Socorro schema for supported crash annotations including
              documentation, access controls, links to data reviews, and links
              to relevant bugs. This information can be seen in the `Crash
              Reporting Data Dictionary
              <https://crash-stats.mozilla.org/documentation/datadictionary/>`__.


   stackwalker
       A command-line minidump processor used by the Socorro processor to
       parse a minidump and generate a JSON-encoded digest of the minidump
       with symbolicated stacks, modules, hardware information, and other
       things.

       .. seealso::

          `rust-minidump <https://github.com/rust-minidump/rust-minidump>`__
              Type definitions, parsing, and analysis for the minidump file format.

          `rust-minidump stackwalker JSON schema <https://github.com/rust-minidump/rust-minidump/blob/main/minidump-processor/json-schema.md>`__
              Schema for the stackwalker output.
