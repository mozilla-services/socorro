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
      "@0x440b8009"
    }

for (line, signature) in expected.iteritems():
    args = map(EmptyFilter, line.split('|'))[1:]
    print args
    f = Frame(1, *args)
    assert f.signature == signature

#
# Test processing the output of minidump_stackwalk
#
assert sampledump.text != None
fh = StringIO.StringIO(sampledump.text)
r = Report()
crashed_thread = r.read_header(fh)
assert r.os_name == "Windows NT"
assert r.os_version == "5.1.2600 Service Pack 2"
assert r.cpu_name == "x86"
assert r.cpu_info == "GenuineIntel family 6 model 14 stepping 8"
assert r.reason == "EXCEPTION_ACCESS_VIOLATION"
assert r.address == "0x0"
assert crashed_thread is not None
assert crashed_thread == '0'

#XXX skip over Module for now

frame_num = 0
loop_count = 0
for line in fh:
    loop_count += 1
    (thread_num, frame_num, module_name, function, source, source_line, instruction) = map(EmptyFilter, line.split('|'))
    if thread_num == crashed_thread and int(frame_num) < 10:
        frame = Frame(r.id,
                      frame_num,
                      module_name,
                      function,
                      source,
                      source_line,
                      instruction)
        r.frames.append(frame)
fh.close()

assert loop_count > 12
print len(r.frames)
assert len(r.frames) == 10
assert r.frames[0].signature == "nsObjectFrame::Instantiate(char const *,nsIURI *)"
