from socorro.models import *

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
