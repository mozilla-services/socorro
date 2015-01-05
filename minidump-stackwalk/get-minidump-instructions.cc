// Copyright (c) 2010 The Mozilla Foundation
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
//     * Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
//     * Neither the name of The Mozilla Foundation nor the names of its
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include <getopt.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <set>
#include <vector>

#include <curl/curl.h>
#include "google_breakpad/processor/basic_source_line_resolver.h"
#include "google_breakpad/processor/minidump.h"
#include "google_breakpad/processor/minidump_processor.h"
#include "google_breakpad/processor/process_state.h"
#include "google_breakpad/processor/stack_frame.h"
#include "google_breakpad/processor/stack_frame_symbolizer.h"
#include "processor/pathname_stripper.h"
#include "processor/simple_symbol_supplier.h"

using namespace google_breakpad;
using std::vector;

CURL* curl;
std::set<string> error_symbols;

void error(const char* fmt, ...)
{
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  fprintf(stderr, "\n");
  va_end(args);

  exit(1);
}

void usage()
{
  fprintf(stderr, "Usage: get-minidump-instructions [options] <minidump> [<symbol paths]\n");
  fprintf(stderr, "Options:\n");
  fprintf(stderr, "\t--disassemble\tAttempt to disassemble the instructions using objdump\n");
  fprintf(stderr, "\t--address=ADDRESS\tShow instructions at ADDRESS\n");
  fprintf(stderr, "\t--help\tDisplay this help text.\n");
}

enum UnmangleType {
  Annotate,
  RawFile,
  LocalFile
};

string unmangle_source_file(const string& source_file, int line,
                            UnmangleType type)
{
  string source_and_line = source_file + ":" + std::to_string(line);
  if (source_file.compare(0, 3, "hg:") != 0) {
    if (type != Annotate) {
      return "";
    }
    return source_and_line;
  }
  string ret = type != Annotate ? "" : source_and_line;
  string s = source_file;
  char* junk = strtok(&s[0], ":");
  char* repo = strtok(nullptr, ":");
  char* path = strtok(nullptr, ":");
  char* rev  = strtok(nullptr, ":");

  if (repo && path && rev) {
    if (type == RawFile) {
      char url[1024];
      snprintf(url, sizeof(url), "http://%s/raw-file/%s/%s",
               repo, rev, path);
      ret = url;
    } else if (type == LocalFile) {
      char filename[1024];
      snprintf(filename, sizeof(filename), "/tmp/%s_%s_%s",
               repo, rev, path);
      char* c;
      while ((c = strchr(filename+5, '/')) != nullptr) {
        *c = '_';
      }
      ret = filename;
    } else {
      char url[1024];
      snprintf(url, sizeof(url), "http://%s/annotate/%s/%s#l%d",
               repo, rev, path, line);
      ret = url;
    }
  }
  return ret;
}

static bool file_exists(const string &file_name)
{
  struct stat sb;
  return stat(file_name.c_str(), &sb) == 0;
}

bool get_line_from_file(const string& file, int line, string& out)
{
  FILE* f = fopen(file.c_str(), "r");
  if (!f) {
    return false;
  }

  char source[1024];
  for (int current = 1; current <= line; current++) {
    if (!fgets(source, sizeof(source), f)) {
      break;
    }
    if (current == line) {
      out = source;
      fclose(f);
      return true;
    }
  }
  fclose(f);
  return false;
}

bool fetch_url_to_file(const string& url, const string& file)
{
  string tempfile = file + ".tmp";
  FILE* f = fopen(tempfile.c_str(), "w");
  if (!f) {
    return false;
  }

  curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
  curl_easy_setopt(curl, CURLOPT_ENCODING, "");
  curl_easy_setopt(curl, CURLOPT_STDERR, stderr);
  curl_easy_setopt(curl, CURLOPT_WRITEDATA, f);
  curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1);

  bool result;
  long retcode = -1;
  if (curl_easy_perform(curl) != 0 ||
      curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &retcode) != 0 ||
      retcode != 200) {
    result = false;
  } else {
    result = true;
  }
  if (!result) {
    return false;
  }
  fclose(f);

  if (rename(tempfile.c_str(), file.c_str()) == 0) {
    return true;
  }

  unlink(tempfile.c_str());
  return false;
}

bool get_line_from_url(const string& url, const string& file,
                       int line, string& out)
{
  // Check for URLs that failed.
  if (error_symbols.find(url) !=
      error_symbols.end()) {
    return false;
  }

  if (!file_exists(file)) {
    // Fetch URL.
    if (!fetch_url_to_file(url, file)) {
      error_symbols.insert(url);
      return false;
    }
  }

  return get_line_from_file(file, line, out);
}

void print_source_line(const string& file, int line)
{
  string url = unmangle_source_file(file, line, RawFile);
  if (url.empty()) {
    return;
  }
  string local_file = unmangle_source_file(file, line, LocalFile);
  string out;
  if (get_line_from_url(url, local_file, line, out)) {
    printf("% 5d %s", line, out.c_str());
  }
}

void print_frame(const StackFrame& frame, const StackFrame& last_frame)
{
  if (!frame.source_file_name.empty()) {
    bool new_file = false;
    if (frame.source_file_name != last_frame.source_file_name) {
      printf("%s\n", unmangle_source_file(frame.source_file_name,
                                          frame.source_line, Annotate).c_str());
      new_file = true;
    }
    if (new_file || frame.source_line != last_frame.source_line) {
      print_source_line(frame.source_file_name, frame.source_line);
    }
  } else if (frame.module &&
             (!last_frame.module ||
              frame.module->code_file() != last_frame.module->code_file())) {
    printf("%s+0x%lx\n", PathnameStripper::File(frame.module->code_file()).c_str(), frame.instruction - frame.module->base_address());
  }
}

int main(int argc, char** argv)
{
  static struct option long_options[] = {
    {"address", required_argument, nullptr, 'a'},
    {"disassemble", no_argument, nullptr, 'd'},
    {"help", no_argument, nullptr, 'h'},
    {nullptr, 0, nullptr, 0}
  };

  bool disassemble = false;
  char* address_arg = nullptr;
  int arg;
  int option_index = 0;
  while((arg = getopt_long(argc, argv, "", long_options, &option_index))
        != -1) {
    switch(arg) {
    case 0:
      if (long_options[option_index].flag != 0)
          break;
      break;
    case 'd':
      disassemble = true;
      break;
    case 'a':
      address_arg = optarg;
      break;
    case 'h':
      usage();
      return 0;
    case '?':
      break;
    default:
      fprintf(stderr, "Unknown option: -%c\n", (char)arg);
      usage();
      return 1;
    }
  }

  if (optind >= argc) {
    usage();
    return 1;
  }

  const char* minidump_file = argv[optind];
  Minidump minidump(minidump_file);
  if (!minidump.Read()) {
    error("Couldn't read minidump %s", minidump_file);
  }

  vector<string> symbol_paths;
  // allow symbol paths to be passed on the commandline.
  for (int i = optind + 1; i < argc; i++) {
    symbol_paths.push_back(argv[i]);
  }

  MinidumpMemoryList* memory_list = minidump.GetMemoryList();
  if (!memory_list) {
    error("Minidump %s doesn't contain a memory list", minidump_file);
  }
  MinidumpModuleList* module_list = minidump.GetModuleList();
  if (!module_list) {
    error("Minidump %s doesn't contain a module list", minidump_file);
  }

  u_int64_t instruction_pointer;
  if (address_arg) {
     instruction_pointer = strtoull(address_arg, NULL, 16);
     arg++;
  } else {
    MinidumpException* exception = minidump.GetException();
    if (!exception) {
      error("Minidump doesn't contain exception information");
    }
    MinidumpContext* context = exception->GetContext();
    if (!context->GetInstructionPointer(&instruction_pointer)) {
      error("Couldn't get instruction pointer. Unknown CPU?");
    }
  }
  MinidumpMemoryRegion* region =
    memory_list->GetMemoryRegionForAddress(instruction_pointer);
  if (!region) {
    error("Minidump doesn't contain a memory region that contains "
          "the instruction pointer from the exception record");
  }

  printf("Faulting instruction pointer: 0x%08lx\n", instruction_pointer);
  const u_int8_t* bytes = region->GetMemory();
  if (disassemble) {
    curl = curl_easy_init();
    char tempfile[1024] = "/tmp/minidump-instructions-XXXXXX";
    int fd = mkstemp(tempfile);
    write(fd, bytes, region->GetSize());
    close(fd);
    const char* arch;
    const char* archopts = "";
    const char* objdump = "objdump";
    uint32_t cpu;
    minidump.GetContextCPUFlagsFromSystemInfo(&cpu);
    switch (cpu) {
    case MD_CONTEXT_X86:
      arch = "i386";
      archopts = "att-mnemonic,i386,addr32,data32";
      break;
    case MD_CONTEXT_AMD64:
      arch = "i386:x86-64";
      archopts = "att-mnemonic,x86-64";
      break;
    case MD_CONTEXT_ARM:
      //XXX: might not work everywhere
      //"arm-linux-gnueabi-objdump"
      objdump = "arm-linux-androideabi-objdump";
      arch = "arm";
      //XXX: not sure how to tell whether force-thumb is needed
      archopts = "reg-names-std,force-thumb";
      break;
    default:
      error("Unknown CPU architecture");
    }
    char cmdline[1024];
    sprintf(cmdline, "%s -b binary -m %s -M %s --adjust-vma=0x%lx -D \"%s\"",
            objdump, arch, archopts, region->GetBase(), tempfile);
    FILE* fp = popen(cmdline, "r");
    if (!fp) {
      error("Couldn't launch objdump");
    }
    SimpleSymbolSupplier supplier(symbol_paths);
    BasicSourceLineResolver resolver;
    StackFrameSymbolizer symbolizer(&supplier, &resolver);
    SystemInfo system_info;
    MinidumpProcessor::GetCPUInfo(&minidump, &system_info);
    MinidumpProcessor::GetOSInfo(&minidump, &system_info);
    StackFrame last_frame = {};
    char line[LINE_MAX];
    bool printed_highlight = false;
    while (fgets(line, LINE_MAX, fp) != nullptr) {
      const char* p = strchr(line, ':');
      StackFrame frame = {};
      if (p && (p - line == 8 || p - line == 16) && !strstr(line, "<.data>:")) {
        frame.instruction = strtoull(line, nullptr, 16);
        symbolizer.FillSourceLineInfo(module_list,
                                      &system_info,
                                      &frame);
        print_frame(frame, last_frame);
        last_frame = frame;
      }
      printf("%s", line);
      if (frame.instruction >= instruction_pointer && !printed_highlight) {
        int l = strlen(line);
        for (int i = 0; i < l; i++) {
          if (line[i] == '\t') {
            putc('\t', stdout);
          } else {
            putc('^', stdout);
          }
        }
        printf("\n");
        printed_highlight = true;
      }
    }
    unlink(tempfile);
    if (pclose(fp) == -1) {
      error("Error running objdump");
    }
    curl_easy_cleanup(curl);
  } else {
    printf("Memory:");
    const int kBytesPerLine = 16;
    for (unsigned int i = 0; i < region->GetSize(); i++) {
      if ((i % kBytesPerLine) == 0) {
        printf("\n%08lx  ", region->GetBase() + i);
      }
      printf("%02x ", bytes[i]);
    }
    printf("\n");
  }
  return 0;
}
