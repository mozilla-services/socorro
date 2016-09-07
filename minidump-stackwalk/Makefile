BREAKPAD_SRCDIR := ../stackwalk/src
BREAKPAD_OBJDIR := ../stackwalk
BREAKPAD_LIBS := \
  $(BREAKPAD_OBJDIR)/lib/libbreakpad.a \
  $(BREAKPAD_OBJDIR)/lib/libdisasm.a \
  $(NULL)

JSON_DIR := jsoncpp-src-0.5.0
JSON_SRCDIR := $(JSON_DIR)/src/lib_json
JSON_INCLUDEDIR := $(JSON_DIR)/include

BINS := \
  stackwalker \
  dumplookup \
  get-minidump-instructions \
  jit-crash-categorize \
  $(NULL)

all: $(BINS)

stackwalker_OBJS := \
  json_reader.o \
  json_value.o \
  json_writer.o \
  $(NULL)

EXTRA_OBJS := \
  http_symbol_supplier.o \
  $(NULL)

VPATH += $(JSON_SRCDIR)

OS := $(shell uname -s)
ifeq ($(OS),Linux)
CURL_CFLAGS := $(shell pkg-config libcurl --cflags)
CURL_LIBS := $(shell pkg-config libcurl --libs)
# Don't -Werror everywhere, some compilers are too picky.
WERROR := -Werror
else
CURL_LIBS := -lcurl
endif

CXXFLAGS += \
  -I$(BREAKPAD_SRCDIR) \
  -I$(JSON_INCLUDEDIR) \
  -D__STDC_FORMAT_MACROS=1 \
  -std=gnu++0x \
  -Wno-format \
  $(WERROR) \
  $(CURL_CFLAGS) \
  $(NULL)
LIBS := $(CURL_LIBS)

.SECONDEXPANSION:
$(BINS): %: %.cc $(BREAKPAD_LIBS) $(EXTRA_OBJS) $$($$*_OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $< $(EXTRA_OBJS) $(BREAKPAD_LIBS) $($*_OBJS) $(LIBS)

clean:
	$(RM) $(BINS) *.o
