from socorro.models import *
from socorro.lib import EmptyFilter
import sampledump
import StringIO

expected = {
    "0|0|libxpcom_core.so|NS_InitXPCOM3_P|nsXPComInit.cpp|549|0x440b8009":
      "NS_InitXPCOM3_P",
    "0|0|libxpcom_core.so||nsXPComInit.cpp|549|0x440b8009":
      "nsXPComInit.cpp#549",
    "0|0|libxpcom_core.so||||0x440b8009":
      "libxpcom_core.so@0x440b8009",
    "0|0|||||0x440b8009":
      "@0x440b8009",
    "0|0|libxul.so|nsCSSFrameConstructor::CreateInputFrame(nsFrameConstructorState &,nsIContent *,nsIFrame *,nsIAtom *,nsStyleContext *,nsIFrame * *,nsStyleDisplay const *,int &,int &,nsFrameItems &)|nsCSSFrameConstructor.cpp|10001|0x12345678":
      "nsCSSFrameConstructor::CreateInputFrame(nsFrameConstructorState&, nsIContent*, nsIFrame*, nsIAtom*, nsStyleContext*, nsIFrame**, nsStyleDisplay const*, int&, int&, nsFrameItems&)",
    "0|0|libxul.so|nsCSSFrameConstructor::CreateInputFrame(nsFrameConstructorState &,nsIContent *,nsIFrame *,nsIAtom *,nsStyleContext *,nsIFrame * *,nsStyleDisplay const *,int &,int &,nsFrameItems &)|nsCSSFrameConstructor.cpp|10001|0x12345678":
      "nsCSSFrameConstructor::CreateInputFrame(nsFrameConstructorState&, nsIContent*, nsIFrame*, nsIAtom*, nsStyleContext*, nsIFrame**, nsStyleDisplay const*, int&, int&, nsFrameItems&)"
    }

for (line, signature) in expected.iteritems():
    args = map(EmptyFilter, line.split('|'))[2:]
    print args
    f = Frame(*args)
    assert f['signature'] == signature

#
# Test processing the output of minidump_stackwalk
#
assert sampledump.text != None
r = Report()
r['dump'] = sampledump.text
r.read_dump()

assert r['os_name'] == "Windows NT"
assert r['os_version'] == "5.1.2600 Service Pack 2"
assert r['cpu_name'] == "x86"
assert r['cpu_info'] == "GenuineIntel family 6 model 14 stepping 8"
assert r['reason'] == "EXCEPTION_ACCESS_VIOLATION"
assert r['address'] == "0x0"
assert r.crashed_thread == 0
assert len(r.modules) == 114 # there are 115 lines, with one bogus module

print len(r.threads)
assert len(r.threads) == 16
assert r.threads[0][0]['signature'] == "nsObjectFrame::Instantiate(char const*, nsIURI*)"
assert len(r.threads[0]) == 12
