from socorro.models import *
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
    f = Frame()
    f.readline(line)
    assert f.signature() == signature

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
assert crashed_thread == 0

#XXX skip over Module for now

frame_num = 0
loop_count = 0
for line in fh:
    loop_count += 1
    if line.startswith(str(crashed_thread)):
        frame = Frame()
        frame.readline(line[0:-1])
        frame.report_id = r.id
        r.frames.append(frame)
        frame_num += 1
fh.close()

assert loop_count > 12
assert frame_num == 12
assert len(r.frames) == 12
assert r.frames[0].thread_num == "0"
assert r.frames[0].module_name == "gklayout.dll"
assert r.frames[0].function == "nsObjectFrame::Instantiate(char const *,nsIURI *)"
assert r.frames[0].source == r"c:\firefox\mozilla\layout\generic\nsobjectframe.cpp"
assert r.frames[0].source_line == "1348"
assert r.frames[0].instruction == "0x24"
