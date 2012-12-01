# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime as datetime
import gzip
import os
import shutil
import time

import unittest
from nose.tools import *

import socorro.unittest.testlib.createJsonDumpStore as createJDS
import socorro.unittest.testlib.util as tutil

import socorro.lib.util as socorro_util
import socorro.external.filesystem.processed_dump_storage as dumpStorage
from socorro.lib.datetimeutil import utc_now, UTC


#def setup_module():
  #tutil.nosePrintModule(__file__)

bogusData= {
  "signature": "nsThread::ProcessNextEvent(int, int*)",
  "uuid": "not in my back yard",
  "date_processed": "2009-03-31 14:45:09.215601",
  "install_age": 100113,
  "uptime": 7,
  "last_crash": 95113,
  "product": "Thunderbird",
  "version": "3.0b2",
  "build_id": "20090223121634",
  "branch": "1.9.1",
  "os_name": "Mac OS X",
  "os_version": "10.5.6 9G55",
  "cpu_name": "x86",
  "cpu_info":	"GenuineIntel family 6 model 15 stepping 6",
  "crash_reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
  "crash_address": "0xe9b246",
  "User Comments": "This thing crashed.\nHelp me Kirk.",
  "app_notes": "",
  "success": True,
  "truncated": True,
  "processor_notes": "",
  "distributor":"",
  "distributor_version": "",
  "dump":"OS|Mac OS X|10.5.6 9G55\nCPU|x86|GenuineIntel family 6 model 15 stepping 6|2\nCrash|EXC_BAD_ACCESS / KERN_INVALID_ADDRESS|0xe9b246|0\nModule|thunderbird-bin||thunderbird-bin|57E2541E130E4A6ABA7A66E16DD0F79F0|0x00001000|0x00c40fff|1\nModule|Cocoa||Cocoa|E064F94D969CE25CB7DE3CFB980C32490|0x00d7a000|0x00d7afff|0\nModule|libmozjs.dylib||libmozjs.dylib|F69DA57AFA0A404880BF4A765E9E09090|0x00d7e000|0x00e39fff|0\nModule|libxpcom.dylib||libxpcom.dylib|55F6A143264C4B8EADBB7D789C8905260|0x00e56000|0x00e56fff|0\nModule|libxpcom_core.dylib||libxpcom_core.dylib|2CC80C82B4304EA0B757E6A0E3CCB8130|0x00e5b000|0x00ec8fff|0\nModule|libplds4.dylib||libplds4.dylib|7A7A59FAC31B48F0A76B00220784A3CE0|0x00eec000|0x00ef1fff|0\nModule|libplc4.dylib||libplc4.dylib|54972A9756C042A0803B41260DDC16F90|0x00ef6000|0x00efbfff|0\nModule|libnspr4.dylib||libnspr4.dylib|1EA68C7035DF4D47B8E3365DD16AF2480|0x00f01000|0x00f27fff|0\nModule|SystemConfiguration||SystemConfiguration|8B26EBF26A009A098484F1ED01EC499C0|0x00f37000|0x00f6efff|0\nModule|Carbon||Carbon|98A5E3BC0C4FA44BBB09713BB88707FE0|0x00f8d000|0x00f8dfff|0\nModule|AddressBook||AddressBook|60DDAE72A1DF8DDBC5C53DF92F372B760|0x00f91000|0x01110fff|0\nModule|QuickTime||QuickTime|BC0920ABBBAAD03F5513AC7FFBD306330|0x011ec000|0x01511fff|0\nModule|IOKit||IOKit|F9F5F0D070E197A832D86751E1D445450|0x015d7000|0x01662fff|0\nModule|libcrypto.0.9.7.dylib||libcrypto.0.9.7.dylib|69BC2457AA23F12FA7D052601D48FA290|0x01688000|0x0173afff|0\nModule|libcups.2.dylib||libcups.2.dylib|16BEC7C6A004F744804E2281A1B1C0940|0x01789000|0x017b1fff|0\nModule|CoreAudio||CoreAudio|F35477A5E23DB0FA43233C37DA01AE1C0|0x017bc000|0x01839fff|0\nModule|AudioToolbox||AudioToolbox|E1BBA7B890E8B8EEC3E3EE900773B7710|0x0188e000|0x019e0fff|0\nModule|AudioUnit||AudioUnit|880380CB87BE2B31914A5934EB3BA6BA0|0x01a55000|0x01a55fff|0\nModule|libsmime3.dylib||libsmime3.dylib|382327EE00224E038C8C1FDD0012DEF50|0x01a5a000|0x01a6ffff|0\nModule|libssl3.dylib||libssl3.dylib|37026155F0D04D6E983982A0AD28E35D0|0x01a7c000|0x01aa3fff|0\nModule|libnss3.dylib||libnss3.dylib|C96CB0108FC14F458CCD31FC6943D4FF0|0x01aae000|0x01b7cfff|0\nModule|libnssutil3.dylib||libnssutil3.dylib|CAF0F4B360B2437194780F72B09E66E40|0x01ba6000|0x01bb2fff|0\nModule|libsoftokn3.dylib||libsoftokn3.dylib|60D20BEB4EF949518B089C1AF864F8670|0x01bbc000|0x01be4fff|0\nModule|libldap60.dylib||libldap60.dylib|F8737FDA25F94DE783A9ABBC9975A8F90|0x01bed000|0x01c15fff|0\nModule|libprldap60.dylib||libprldap60.dylib|703DD9D1527041C0BB089FBCAD19F1F70|0x01c21000|0x01c26fff|0\nModule|libldif60.dylib||libldif60.dylib|42C22A365F58422D9BDE93C75761F2370|0x01c2c000|0x01c30fff|0\nModule|libsqlite3.dylib||libsqlite3.dylib|778D1BC8256143779AB80CCB9D42C8A70|0x01c35000|0x01c96fff|0\nModule|libstdc++.6.dylib||libstdc++.6.dylib|04B812DCEC670DAA8B7D2852AB14BE600|0x01c9e000|0x01cfbfff|0\nModule|libgcc_s.1.dylib||libgcc_s.1.dylib|F53C808E87D1184C0F9DF63AEF53CE0B0|0x01d4c000|0x01d53fff|0\nModule|libSystem.B.dylib||libSystem.B.dylib|D68880DFB1F8BECDBDAC6928DB1510FB0|0x01d59000|0x01ec0fff|0\nModule|AppKit||AppKit|A3A300499BBE4F1DFEBF71D752D019160|0x01f4f000|0x0274dfff|0\nModule|CoreData||CoreData|8E28162EF2288692615B52ACC01F8B540|0x02c8e000|0x02d73fff|0\nModule|ApplicationServices||ApplicationServices|8F910FA65F01D401AD8D04CC933CF8870|0x02dee000|0x02deefff|0\nModule|DesktopServicesPriv||DesktopServicesPriv|D16642BA22C32F67BE793EBFBE67CA3A0|0x02df6000|0x02e80fff|0\nModule|Foundation||Foundation|8FE77B5D15ECDAE1240B4CB604FC6D0B0|0x02ecb000|0x03146fff|0\nModule|HIToolbox||HIToolbox|3747086BA21EE419708A5CAB946C8BA60|0x032a4000|0x035acfff|0\nModule|QuartzCore||QuartzCore|2FED2DD7565C84A0F0C608D41D4D172C0|0x0370a000|0x03aa7fff|0\nModule|Security||Security|55DDA7486DF4E8E1D61505BE16F83A1C0|0x03ba1000|0x03d6ffff|0\nModule|SpeechRecognition||SpeechRecognition|D3180F9EDBD9A5E6F283D6156AA3C6020|0x03eb4000|0x03ebdfff|0\nModule|libauto.dylib||libauto.dylib|42D8422DC23A18071869FDF7B5D8FAB50|0x03ec7000|0x03ef2fff|0\nModule|libicucore.A.dylib||libicucore.A.dylib|18098DCF431603FE47EE027A60006C850|0x03f00000|0x04038fff|0\nModule|libxml2.2.dylib||libxml2.2.dylib|D69560099D9EB32BA7F8A17BAA65A28D0|0x0408c000|0x0416dfff|0\nModule|libz.1.dylib||libz.1.dylib|5DDD8539AE2EBFD8E7CC1C57525385C70|0x0419a000|0x041a8fff|0\nModule|CoreUI||CoreUI|676FAF4FF6DDDBDD7D716FCE0E59349A0|0x041ae000|0x041e8fff|0\nModule|DiskArbitration||DiskArbitration|75B0C8D8940A8A27816961DDDCAC8E0F0|0x04208000|0x04210fff|0\nModule|CoreServices||CoreServices|2FCC8F3BD5BBFC000B476CAD8E6A3DD20|0x0421a000|0x0421afff|0\nModule|libobjc.A.dylib||libobjc.A.dylib|7B92613FDF804FD9A0A3733A0674C30B0|0x04222000|0x04302fff|0\nModule|CoreFoundation||CoreFoundation|4A70C8DBB582118E31412C53DC1F407F0|0x04374000|0x044a7fff|0\nModule|ATS||ATS|8C51DE0EC3DEAEF416578CD59DF387540|0x0459f000|0x04632fff|0\nModule|ColorSync||ColorSync|FD78C64B42F804AE9B0BAE75AAD2C5100|0x04659000|0x04724fff|0\nModule|CoreGraphics||CoreGraphics|3A91D1037AFDE01D1D8ACDF9CD1CAA140|0x04765000|0x04e05fff|0\nModule|CoreText||CoreText|F9A90116AE34A2B0D84E87734766FB3A0|0x04ed5000|0x04f2ffff|0\nModule|HIServices||HIServices|01B690D1F376E400AC873105533E39EB0|0x04f6f000|0x04fc0fff|0\nModule|ImageIO||ImageIO|6A6623D3D1A7292B5C3763DCD108B55F0|0x04fea000|0x05130fff|0\nModule|LangAnalysis||LangAnalysis|8B7831B5F74A950A56CF2D22A2D436F60|0x05188000|0x05198fff|0\nModule|QD||QD|B743398C24C38E581A86E91744A2BA6E0|0x051a5000|0x0524cfff|0\nModule|SpeechSynthesis||SpeechSynthesis|06D8FC0307314F8FFC16F206AD3DBF440|0x05275000|0x05285fff|0\nModule|CarbonCore||CarbonCore|F06FE5D92D56AC5AA52D1BA1827459240|0x05294000|0x0556efff|0\nModule|CFNetwork||CFNetwork|80851410A5592B7C3B149B2FF849BCC10|0x055d8000|0x05675fff|0\nModule|Metadata||Metadata|E0572F20350523116F23000676122A8D0|0x056ed000|0x05736fff|0\nModule|OSServices||OSServices|2A135D4FB16F4954290F7B72B4111AA30|0x05752000|0x0580cfff|0\nModule|SearchKit||SearchKit|3140A605DB2ABF56B237FA156A08B28B0|0x05871000|0x058f0fff|0\nModule|AE||AE|4CB9EF65CF116D6DD424F0CE98C2D0150|0x05933000|0x05962fff|0\nModule|LaunchServices||LaunchServices|6F9629F4ED1BA3BB313548E6838B28880|0x0597a000|0x05a06fff|0\nModule|DictionaryServices||DictionaryServices|AD0AA0252E3323D182E17F50DEFE56FC0|0x05a4c000|0x05a62fff|0\nModule|libmathCommon.A.dylib||libmathCommon.A.dylib|D75DC85A7C3CA075A24E7252869B76600|0x05a74000|0x05a78fff|0\nModule|libbsm.dylib||libbsm.dylib|D25C63378A5029648FFD4B4669BE31BF0|0x05a7c000|0x05a83fff|0\nModule|libsqlite3.0.dylib||libsqlite3.0.dylib|6978BBCCA4277D6AE9F042BEFF643F7D0|0x05a8a000|0x05b11fff|0\nModule|libxslt.1.dylib||libxslt.1.dylib|0A9778D6368AE668826F446878DEB99B0|0x05b1e000|0x05b42fff|0\nModule|Accelerate||Accelerate|274CA63B852C0701F86FDB679198FDDB0|0x05b4c000|0x05b4cfff|0\nModule|vImage||vImage|2A2C9E354B6491A892802B0BD97F1CC80|0x05b50000|0x05c17fff|0\nModule|vecLib||vecLib|274CA63B852C0701F86FDB679198FDDB0|0x05c27000|0x05c27fff|0\nModule|libvMisc.dylib||libvMisc.dylib|2C407027985293C0B174294688D390650|0x05c2b000|0x05ca8fff|0\nModule|libvDSP.dylib||libvDSP.dylib|B232C018DDD040EC4E2C2AF632DD497F0|0x05cb6000|0x05ce3fff|0\nModule|libBLAS.dylib||libBLAS.dylib|3769D952F2378FCA4FCCAA61527C8ACF0|0x05cef000|0x060fffff|0\nModule|libLAPACK.dylib||libLAPACK.dylib|9B0ED359D604DC6CA6389560C0BC679F0|0x06145000|0x06503fff|0\nModule|libJPEG.dylib||libJPEG.dylib|E7EB56555109E23144924CD64AA8DAEC0|0x06539000|0x06558fff|0\nModule|libTIFF.dylib||libTIFF.dylib|3589442575AC77746AE99ECF724F5F870|0x06560000|0x0659ffff|0\nModule|libGIF.dylib||libGIF.dylib|572A32E46E33BE1EC041C5EF5B0341AE0|0x065aa000|0x065aefff|0\nModule|libPng.dylib||libPng.dylib|4780E979D35AA5EC2CEA22678836CEA50|0x065b4000|0x065cffff|0\nModule|libRadiance.dylib||libRadiance.dylib|8A844202FCD65662BB9AB25F08C45A620|0x065d7000|0x065d9fff|0\nModule|libresolv.9.dylib||libresolv.9.dylib|A8018C42930596593DDF27F7C20FE7AF0|0x065de000|0x065fcfff|0\nModule|vecLib||vecLib|274CA63B852C0701F86FDB679198FDDB0|0x06606000|0x06606fff|0\nModule|InstallServer||InstallServer|A0358A24A32E1E9813A1575185B3398F0|0x0660a000|0x0660afff|0\nModule|CarbonSound||CarbonSound|0F2BA6E891D3761212CF5A5E6134D6830|0x0660e000|0x06618fff|0\nModule|OpenGL||OpenGL|7E5048A2677B41098C84045305F42F7F0|0x06621000|0x0662efff|0\nModule|libGLImage.dylib||libGLImage.dylib|1123B8A48BCBE9CC7AA8DD8E1A214A660|0x06636000|0x06674fff|0\nModule|libffi.dylib||libffi.dylib|A3B573EB950CA583290F7B2B4C486D090|0x0667e000|0x0667ffff|0\nModule|CoreVideo||CoreVideo|C0D869876AF51283A160CD2224A23ABF0|0x06684000|0x0669cfff|0\nModule|libGLU.dylib||libGLU.dylib|7C4BC24ABDD4C859788D6874F906D5190|0x066b0000|0x06709fff|0\nModule|libGL.dylib||libGL.dylib|AB2164E7650463E7167B603B325B409C0|0x0671d000|0x06729fff|0\nModule|libGLProgrammability.dylib||libGLProgrammability.dylib|5D283543AC844E7C6FA3440AC56CD2650|0x06737000|0x06c08fff|0\nModule|CommonPanels||CommonPanels|EA0665F57CD267609466ED8B2B20E8930|0x06d35000|0x06d3afff|0\nModule|Help||Help|B507B08E484CB89033E9CF23062D77DE0|0x06d43000|0x06d46fff|0\nModule|HTMLRendering||HTMLRendering|FE87A9DEDE38DB00E6C8949942C6BD4F0|0x06d4c000|0x06da8fff|0\nModule|ImageCapture||ImageCapture|0C71CF9C4A8D4A4A763DC52E7C4703870|0x06dd6000|0x06debfff|0\nModule|Ink||Ink|BF3FA8927B4B8BAAE92381A976FD20790|0x06e06000|0x06e99fff|0\nModule|NavigationServices||NavigationServices|91844980804067B07A0B6124310D3F310|0x06eb8000|0x06efafff|0\nModule|OpenScripting||OpenScripting|572C7452D7E740E8948A5AD07A99602B0|0x06f28000|0x06f40fff|0\nModule|SecurityHI||SecurityHI|2B2854123FED609D1820D2779E2E09630|0x06f52000|0x06f54fff|0\nModule|DirectoryService||DirectoryService|F8931F64103C8A86B82E9714352F43230|0x06f5a000|0x06f78fff|0\nModule|LDAP||LDAP|CC04500CF7B6EDCCC75BB3FE2973F72C0|0x06f85000|0x06fb7fff|0\nModule|DSObjCWrappers||DSObjCWrappers|09DEB9E32D0D09DFB95AE569BDD2B7A40|0x06fc2000|0x06fd1fff|0\nModule|Backup||Backup|60FDC2CDE17C2689677F2DCFD592407D0|0x06fdf000|0x06fe4fff|0\nModule|libsasl2.2.dylib||libsasl2.2.dylib|BB7971CA2F609C070F87786A93D1041E0|0x06fee000|0x06ffdfff|0\nModule|libssl.0.9.7.dylib||libssl.0.9.7.dylib|C7359B7AB32B5F8574520746E10A41CC0|0x07005000|0x07029fff|0\nModule|libalerts_s.dylib||libalerts_s.dylib|129E11DF8E9E4DABA8DA0F4E41769CEB0|0x07308000|0x07313fff|0\nModule|Unicode Encodings||Unicode Encodings|542F2B8930D6BDF16C318FFEA541ACAB0|0x07395000|0x07396fff|0\nModule|libSimplifiedChineseConverter.dylib||libSimplifiedChineseConverter.dylib|548D5A699DBE2BB8FCC8275321FDC0D40|0x073ae000|0x073bcfff|0\nModule|HelpData||HelpData|28D5C89696B963716210925D91D4A26D0|0x073e4000|0x073f0fff|0\nModule|Shortcut||Shortcut|057783867138902B52BC0941FEDB74D10|0x07500000|0x07528fff|0\nModule|libCGATS.A.dylib||libCGATS.A.dylib|386DCE4B28448FB86E33E06AC466F4D80|0x077c6000|0x077cdfff|0\nModule|libRIP.A.dylib||libRIP.A.dylib|5D0B5AF7992E14DE017F9A9C7CB059600|0x1f885000|0x1f8c6fff|0\nModule|libCSync.A.dylib||libCSync.A.dylib|E6ACEED359BD228F42BC1246AF5919C90|0x1f8d3000|0x1f8defff|0\nModule|Kerberos||Kerberos|685CC018C133668D0D3AC6A1CB63CFF90|0x20000000|0x200b0fff|0\nModule|libnssdbm3.dylib||libnssdbm3.dylib|2312FD8609554909A693BA9248E6E8420|0x213de000|0x213fafff|0\nModule|libfreebl3.dylib||libfreebl3.dylib|85DA857F16A34E85A40D3042EE4866AA0|0x21469000|0x214c9fff|0\nModule|libnssckbi.dylib||libnssckbi.dylib|A68FB6ED4263406096AD73E9A2D2B5C40|0x214d1000|0x21509fff|0\nModule|RawCamera||RawCamera|FEA6D22F985AEC2F376D937291B54ECC0|0x222c0000|0x22492fff|0\nModule|Print||Print|8BF7EF71216376D12FCD5EC17E43742C0|0x64b00000|0x64b06fff|0\nModule|libJapaneseConverter.dylib||libJapaneseConverter.dylib|7B0248C392848338F5D6ED093313EEEF0|0xba900000|0xba916fff|0\nModule|PrintCore||PrintCore|222DADE7B33B99708B8C09D1303F93FC0|0xfa100000|0xfa17afff|0\n\n0|0|libxpcom_core.dylib|nsThread::ProcessNextEvent(int, int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|510|0x5\n0|1|libxpcom_core.dylib|NS_ProcessPendingEvents_P(nsIThread*, unsigned int)|nsThreadUtils.cpp|180|0x16\n0|2|thunderbird-bin|nsBaseAppShell::NativeEventCallback()|hg:hg.mozilla.org/releases/mozilla-1.9.1:widget/src/xpwidgets/nsBaseAppShell.cpp:c1141fd20875|121|0x17\n0|3|thunderbird-bin|nsAppShell::ProcessGeckoEvents(void*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:widget/src/cocoa/nsAppShell.mm:c1141fd20875|374|0x7\n0|4|CoreFoundation||||0x735f4\n0|5|CoreFoundation||||0x73cd7\n0|6|HIToolbox||||0x302bf\n0|7|HIToolbox||||0x300d8\n0|8|HIToolbox||||0x2ff4c\n0|9|AppKit||||0x40d7c\n0|10|AppKit||||0x4062f\n0|11|AppKit||||0x3966a\n0|12|thunderbird-bin|nsAppShell::Run()|hg:hg.mozilla.org/releases/mozilla-1.9.1:widget/src/cocoa/nsAppShell.mm:c1141fd20875|693|0x79\n0|13|thunderbird-bin|nsAppStartup::Run()|hg:hg.mozilla.org/releases/mozilla-1.9.1:toolkit/components/startup/src/nsAppStartup.cpp:c1141fd20875|192|0x7\n0|14|thunderbird-bin|XRE_main|hg:hg.mozilla.org/releases/mozilla-1.9.1:toolkit/xre/nsAppRunner.cpp:c1141fd20875|3279|0x7\n0|15|thunderbird-bin|main|/builds/releases/3.0b2/2/comm-central/mail/app/nsMailApp.cpp|103|0x18\n0|16|thunderbird-bin||||0x2105\n0|17|thunderbird-bin||||0x202c\n0|18|||||0x1\n1|0|libSystem.B.dylib||||0x3830a\n1|1|libnspr4.dylib|poll|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/md/unix/unix.c:c1141fd20875|3672|0x2f\n1|2|libnspr4.dylib|_pr_poll_with_poll|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptio.c:c1141fd20875|3916|0x15\n1|3|libnspr4.dylib|PR_Poll|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptio.c:c1141fd20875|4318|0x18\n1|4|thunderbird-bin|nsSocketTransportService::Poll(int, unsigned int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:netwerk/base/src/nsSocketTransportService2.cpp:c1141fd20875|355|0xf\n1|5|thunderbird-bin|nsSocketTransportService::DoPollIteration(int)|hg:hg.mozilla.org/releases/mozilla-1.9.1:netwerk/base/src/nsSocketTransportService2.cpp:c1141fd20875|660|0x18\n1|6|thunderbird-bin|nsSocketTransportService::OnProcessNextEvent(nsIThreadInternal*, int, unsigned int)|hg:hg.mozilla.org/releases/mozilla-1.9.1:netwerk/base/src/nsSocketTransportService2.cpp:c1141fd20875|539|0xf\n1|7|libxpcom_core.dylib|nsThread::ProcessNextEvent(int, int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|497|0x25\n1|8|libxpcom_core.dylib|NS_ProcessNextEvent_P(nsIThread*, int)|nsThreadUtils.cpp|227|0x15\n1|9|thunderbird-bin|nsSocketTransportService::Run()|hg:hg.mozilla.org/releases/mozilla-1.9.1:netwerk/base/src/nsSocketTransportService2.cpp:c1141fd20875|581|0x12\n1|10|libxpcom_core.dylib|nsThread::ProcessNextEvent(int, int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|510|0x7\n1|11|libxpcom_core.dylib|NS_ProcessNextEvent_P(nsIThread*, int)|nsThreadUtils.cpp|227|0x15\n1|12|libxpcom_core.dylib|nsThread::ThreadFunc(void*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|254|0xf\n1|13|libnspr4.dylib|_pt_root|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptthread.c:c1141fd20875|221|0x8\n1|14|libSystem.B.dylib||||0x32094\n1|15|libSystem.B.dylib||||0x31f51\n2|0|libSystem.B.dylib||||0x1226\n2|1|libSystem.B.dylib||||0x7daae\n2|2|libnspr4.dylib|pt_TimedWait|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|280|0x18\n2|3|libnspr4.dylib|PR_WaitCondVar|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|407|0x17\n2|4|libxpcom_core.dylib|TimerThread::Run()|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/TimerThread.cpp:c1141fd20875|345|0xe\n2|5|libxpcom_core.dylib|nsThread::ProcessNextEvent(int, int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|510|0x7\n2|6|libxpcom_core.dylib|NS_ProcessNextEvent_P(nsIThread*, int)|nsThreadUtils.cpp|227|0x15\n2|7|libxpcom_core.dylib|nsThread::ThreadFunc(void*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|254|0xf\n2|8|libnspr4.dylib|_pt_root|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptthread.c:c1141fd20875|221|0x8\n2|9|libSystem.B.dylib||||0x32094\n2|10|libSystem.B.dylib||||0x31f51\n3|0|libSystem.B.dylib||||0x120e\n3|1|libSystem.B.dylib||||0x78538\n3|2|libnspr4.dylib|PR_WaitCondVar|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|405|0x10\n3|3|libnspr4.dylib|PR_Wait|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|584|0x11\n3|4|libxpcom_core.dylib|nsEventQueue::GetEvent(int, nsIRunnable**)|../../dist/include/xpcom/nsAutoLock.h|340|0xf\n3|5|libxpcom_core.dylib|nsThread::ProcessNextEvent(int, int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.h:c1141fd20875|112|0x15\n3|6|libxpcom_core.dylib|NS_ProcessNextEvent_P(nsIThread*, int)|nsThreadUtils.cpp|227|0x15\n3|7|libxpcom_core.dylib|nsThread::ThreadFunc(void*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|254|0xf\n3|8|libnspr4.dylib|_pt_root|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptthread.c:c1141fd20875|221|0x8\n3|9|libSystem.B.dylib||||0x32094\n3|10|libSystem.B.dylib||||0x31f51\n4|0|libSystem.B.dylib||||0x1226\n4|1|libSystem.B.dylib||||0x7daae\n4|2|libnspr4.dylib|pt_TimedWait|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|280|0x18\n4|3|libnspr4.dylib|PR_WaitCondVar|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|407|0x17\n4|4|libnspr4.dylib|PR_Wait|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|584|0x11\n4|5|libxpcom_core.dylib|nsThreadPool::Run()|../../dist/include/xpcom/nsAutoLock.h|340|0xd\n4|6|libxpcom_core.dylib|nsThread::ProcessNextEvent(int, int*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|510|0x7\n4|7|libxpcom_core.dylib|NS_ProcessNextEvent_P(nsIThread*, int)|nsThreadUtils.cpp|227|0x15\n4|8|libxpcom_core.dylib|nsThread::ThreadFunc(void*)|hg:hg.mozilla.org/releases/mozilla-1.9.1:xpcom/threads/nsThread.cpp:c1141fd20875|254|0xf\n4|9|libnspr4.dylib|_pt_root|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptthread.c:c1141fd20875|221|0x8\n4|10|libSystem.B.dylib||||0x32094\n4|11|libSystem.B.dylib||||0x31f51\n5|0|libSystem.B.dylib||||0x1226\n5|1|libSystem.B.dylib||||0x7daae\n5|2|libnspr4.dylib|pt_TimedWait|hg:hg.mozilla.org/releases/mozilla-1.9.1:nsprpub/pr/src/pthreads/ptsynch.c:c1141fd20875|280|0x18"
  }

class TestProcessedDumpStorage(unittest.TestCase):
  def setUp(self):
    self.testDir = os.path.join('.','TEST-DUMPSTORAGE')+'/'
    fakeLogger = socorro_util.SilentFakeLogger()
    self.initKwargs =  {
      0:{'logger': fakeLogger,},
      1:{'logger': fakeLogger,'fileSuffix':'DSgz',},
      2:{'logger': fakeLogger,'fileSuffix':'.DSgz',},
      3:{'logger': fakeLogger,'gzipCompression':'3',},
      4:{'logger': fakeLogger,'storageDepth':'3',},
      5:{'logger': fakeLogger,'rootName':'someRoot', 'dateName':'someDate', 'minutesPerSlot':'12'}
      }

    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such test directory
    os.mkdir(self.testDir)

  def tearDown(self):
    pass
    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such test directory

  def dailyFromNow(self):

    return ''.join(utc_now().date().isoformat().split('-'))

  def dailyFromDate(self,dateString):
    """given "YYYY-mm-dd-hh-mm" return YYYYmmdd string"""
    return ''.join(dateString.split('-')[:3])

  def relativeDateParts(self,dateString,minutesPerSlot):
    """ given "YYYY-mm-dd-hh-mm", return [hh,slot]"""
    hh,mm = dateString.split('-')[-2:]
    slot = int(mm) - int(mm)%minutesPerSlot
    return [hh,"%02d"%slot]
  def hourSlotFromNow(self,minutesPerSlot):
    hh,mm = utc_now().isoformat('T').split('T')[1].split(':')[:2]
    slot = int(mm) - int(mm)%minutesPerSlot
    return hh,"%02d"%slot

  def testConstructor(self):
    self.constructorAlt(self.testDir,**self.initKwargs[0])
    self.constructorAlt(self.testDir,**self.initKwargs[1])
    self.constructorAlt(self.testDir,**self.initKwargs[2])
    self.constructorAlt(self.testDir,**self.initKwargs[3])
    self.constructorAlt(self.testDir,**self.initKwargs[4])

  def constructorAlt(self,*args,**kwargs):
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**kwargs)
    assert self.testDir.rstrip(os.sep) == storage.root,'From kwargs=%s'%kwargs
    assert storage.indexName == kwargs.get('indexName','name'),'From kwargs=%s'%kwargs
    suffix = kwargs.get('fileSuffix','.jsonz')
    if not suffix.startswith('.'):suffix = '.%s'%suffix
    assert suffix == storage.fileSuffix,'expected "%s", got "%s" From kwargs=%s'%(suffix,storage.fileSuffix,kwargs)
    compression = int(kwargs.get('gzipCompression','9'))
    assert compression == storage.gzipCompression
    storageDepth = int(kwargs.get('storageDepth',2))
    assert storageDepth == storage.storageDepth,'Expected %s, got %s'%(storageDepth,storage.storageDepth)
    mps = int(kwargs.get('minutesPerSlot',1))
    assert mps == storage.minutesPerSlot,'Expected %s, got %s'%(mps,storage.minutesPerSlot)

  def testNewEntry(self):
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**self.initKwargs[0])
    for ooid,(tdate,wh,pathprefix,longDatePath) in createJDS.jsonFileData.items():
      dailyPart = ''.join(tdate.split('-')[:3])
      expectedDir = os.sep.join((storage.root,dailyPart,storage.indexName,pathprefix))
      expectedPath = os.path.join(expectedDir,"%s%s"%(ooid,storage.fileSuffix))
      hourPart,slot = self.relativeDateParts(tdate,storage.minutesPerSlot)
      datepart = "%s_0"%(os.path.join(hourPart,slot))
      expectedDateDir = os.sep.join((storage.root,dailyPart,storage.dateName,datepart))
      testStamp = datetime.datetime(*[int(x) for x in tdate.split('-')],tzinfo=UTC)
      fh = None
      try:
        fh = storage.newEntry(ooid,testStamp)
        fh.write(expectedPath)
      finally:
        fh.close()
      assert os.path.exists(expectedPath), 'Expected: gzip file %s but none there'%(expectedPath)
      try:
        fh = gzip.open(expectedPath)
        firstline = fh.readline()
        assert expectedPath == firstline, 'Expected this file to contain its own path, but %s'%firstline
        nextline = fh.readline()
        assert '' == nextline, 'Expected this file to contain ONLY its own path, but %s'%nextline
      finally:
        fh.close()
      dToN = os.path.join(expectedDateDir,ooid)
      assert os.path.islink(dToN),'Expected %s to be link exists:%s'%(dToN,os.path.exists(dToN))
      datapath = os.readlink(os.path.join(expectedDateDir,ooid))
      # The next lines prove we have a relative-path link
      zigpath = os.path.join(expectedDateDir,datapath)
      assert os.path.isfile(os.path.join(zigpath,"%s%s"%(ooid,storage.fileSuffix)))
      assert os.path.pardir in zigpath,'But zigpath has no "parent directory" parts?: %s'%(zigpath)

  def testPutDumpToFile(self):
    """
    testPutDumpToFile(self):(slow=2)
    """
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**self.initKwargs[2])
    ooid = '0bae7049-bbff-49f2-dead-7e9fe2081125' # is coded for depth 2, so no special thought needed
    data = createJDS.jsonFileData[ooid]
    stamp = datetime.datetime(*[int(x) for x in data[0].split('-')],tzinfo=UTC)
    expectedPath = os.sep.join((storage.root,self.dailyFromNow(),storage.indexName,data[2]))
    expectedFile = os.path.join(expectedPath,ooid+storage.fileSuffix)
    assert not os.path.exists(expectedPath), 'Better not exist at start of test'
    data = {"header":"header","data":['line ONE','lineTWO','last line']}
    now = utc_now()
    if now.second > 57:
      time.sleep(60-now.second)
    now = utc_now()
    storage.putDumpToFile(ooid,data,now) # default timestamp
    datePath = None
    seenDirs = set()
    seenFiles = set()
    for dirpath, dirnames, filenames in os.walk(storage.root):
      for f in filenames:
        if f.startswith(ooid):
          seenFiles.add(os.path.join(dirpath,f))
      for d in dirnames:
        if d.startswith(ooid):
          seenDirs.add(os.path.join(dirpath,d))

    for p in seenFiles:
      assert storage.fileSuffix in p
      assert storage.indexName in p
    for p in seenDirs:
      assert ooid == os.path.split(p)[1]
      assert storage.dateName in p

    assert os.path.exists(expectedFile), 'Just a nicer way to say your test is FUBAR'
    f = gzip.open(expectedFile)
    lines = " ".join(f.readlines())
    f.close()
    assert """{"header": "header", "data": ["line ONE", "lineTWO", "last line"]}""" == lines

  def testGetDumpPath(self):
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**self.initKwargs[1])
    seq = 0
    seqs = {}
    for ooid,(tdate,wh,pathprefix,longdatepath) in createJDS.jsonFileData.items():
      hh,slot = self.relativeDateParts(tdate,storage.minutesPerSlot)
      seqs[ooid] = seq
      expectedDir = os.sep.join((storage.root,self.dailyFromDate(tdate),storage.dateName,hh,"%s_0"%slot))
      expectedPath = os.path.join(expectedDir,"%s%s"%(ooid,storage.fileSuffix))
      stamp = datetime.datetime(*[int(x) for x in tdate.split('-')],tzinfo=UTC)
      fh = storage.newEntry(ooid,stamp)
      fh.write("Sequence Number %d\n"%seq)
      fh.close()
      seq += 1
    for ooid in createJDS.jsonFileData.keys():
      path = storage.getDumpPath(ooid)
      f = gzip.open(path,'r')
      lines = f.readlines()
      f.close()
      assert 1 == len(lines)
      assert 'Sequence Number %d\n'%(seqs[ooid]) == lines[0],'But expected "Sequence Number %d\n", got "%s"'%(seqs[ooid],lines[0])
    assert_raises(OSError, storage.getDumpPath,createJDS.jsonBadUuid)

  def createDumpSet(self, dumpStorage):
    for ooid,data in createJDS.jsonFileData.items():
      bogusData["uuid"] = ooid
      stamp = datetime.datetime(*[int(x) for x in data[0].split('-')],tzinfo=UTC)
      dumpStorage.putDumpToFile(ooid,bogusData,stamp)

  def testRemoveDumpFile(self):
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**self.initKwargs[0])
    self.createDumpSet(storage)
    expectedCount = len(createJDS.jsonFileData)
    dumpFiles = set()

    # should fail quitely
    storage.removeDumpFile(createJDS.jsonBadUuid)

    ooids = createJDS.jsonFileData.keys()
    for dir,dirs,files in os.walk(storage.root):
      dumpFiles.update(files)
    assert expectedCount == len(dumpFiles)

    #should happily remove them each and all
    for ooid in ooids:
      dumpFiles = set()
      storage.removeDumpFile(ooid)
      expectedCount -= 1
      for dir,dirs,files in os.walk(storage.root):
        dumpFiles.update(files)
      assert expectedCount == len(dumpFiles),'\n   %s: expected %d, but %d\n - %s'%(ooid,expectedCount,len(dumpFiles), '\n - '.join(dumpFiles))

  def testGetDumpFromFile(self):
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**self.initKwargs[0])
    self.createDumpSet(storage)
    o = None
    for ooid in createJDS.jsonFileData.keys():
      o = storage.getDumpFromFile(ooid)
      bogusData['uuid'] = ooid
      assert bogusData == o
    assert_raises(OSError,storage.getDumpFromFile,createJDS.jsonBadUuid)

  def testSecondNewEntryAfterRemove(self):
    storage = dumpStorage.ProcessedDumpStorage(self.testDir,**self.initKwargs[0])
    ooid,(tdate,ig1,pathprefix,longDatePath) = createJDS.jsonFileData.items()[1]
    testStamp = datetime.datetime(*[int(x) for x in tdate.split('-')],tzinfo=UTC)
    fh = storage.newEntry(ooid,testStamp)
    fh.close()
    storage.removeDumpFile(ooid)
    #Next line fails ugly and useless unless we have fixed the problem
    nh = None
    try:
      nh = storage.newEntry(ooid,testStamp)
    finally:
      if nh:
        nh.close()


if __name__ == "__main__":
  unittest.main()
