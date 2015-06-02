// Copyright (c) 2014 The Mozilla Foundation
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

#include "common/scoped_ptr.h"
#include "google_breakpad/processor/basic_source_line_resolver.h"
#include "google_breakpad/processor/minidump.h"
#include "google_breakpad/processor/minidump_processor.h"
#include "google_breakpad/processor/stack_frame_cpu.h"
#include "google_breakpad/processor/system_info.h"
#include "processor/pathname_stripper.h"
#include "processor/simple_symbol_supplier.h"

#include "common.h"
#include "http_symbol_supplier.h"

using namespace google_breakpad;
using breakpad_extra::HTTPSymbolSupplier;

#if (__GNUC__ == 4) && (__GNUC_MINOR__ < 6)
#define nullptr __null
#endif

void error(const char* fmt, ...)
{
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  fprintf(stderr, "\n");
  va_end(args);

  exit(1);
}

void print_frame(const StackFrame* frame) {
  if (frame->module) {
    printf("%s", PathnameStripper::File(frame->module->code_file()).c_str());
    if (!frame->function_name.empty()) {
      printf("!%s", frame->function_name.c_str());
      if (!frame->source_file_name.empty()) {
        string source_file = PathnameStripper::File(frame->source_file_name);
        printf(" [%s : %d + 0x%lx]",
               source_file.c_str(),
               frame->source_line,
               frame->instruction - frame->source_line_base);
      } else {
        printf(" + 0x%lx", frame->instruction - frame->function_base);
      }
    } else {
      printf(" + 0x%lx",
             frame->instruction - frame->module->base_address());
    }
  } else {
    printf("0x%lx", frame->instruction);
  }
  printf("\n");
}

StackFrame* GetStackFrameCPU(SystemInfo& system_info) {
  if (system_info.cpu == "x86") {
    return new StackFrameX86;
  }
  if (system_info.cpu == "amd64") {
    return new StackFrameAMD64;
  }
  if (system_info.cpu == "arm") {
    return new StackFrameARM;
  }
  return NULL;
}

u_int64_t GetStackPointer(const MinidumpContext* context) {
  switch (context->GetContextCPU()) {
  case MD_CONTEXT_X86:
    return context->GetContextX86()->esp;
  case MD_CONTEXT_AMD64:
    return context->GetContextAMD64()->rsp;
  case MD_CONTEXT_ARM:
    return context->GetContextARM()->iregs[MD_CONTEXT_ARM_REG_SP];
  default:
    error("Unsupported CPU type %d", context->GetContextCPU());
    break;
  }
  return 0;
}

void usage()
{
  fprintf(stderr, "Usage: dumplookup [options] <minidump> [<symbol paths]\n");
  fprintf(stderr, "Options:\n");
  fprintf(stderr, "\t--all\tShow all values on the stack.\n");
  http_commandline_usage();
  fprintf(stderr, "\t--help\tDisplay this help text.\n");
}

int main(int argc, char** argv)
{
  static struct option long_options[] = {
    {"all", no_argument, nullptr, 'a'},
    HTTP_COMMANDLINE_OPTIONS
    {"help", no_argument, nullptr, 'h'},
    {nullptr, 0, nullptr, 0}
  };

  // Yeah, this is ugly.
  vector<char*> symbols_urls;
  char* symbols_cache = nullptr;
  const char* symbols_tmp = "/tmp";
  bool show_all = false;

  int arg;
  int option_index = 0;
  while((arg = getopt_long(argc, argv, "", long_options, &option_index))
        != -1) {
    switch(arg) {
    case 0:
      if (long_options[option_index].flag != 0)
          break;
      break;
    case 'a':
      show_all = true;
      break;
    HANDLE_HTTP_COMMANDLINE_OPTIONS
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

  if (!check_http_commandline_options(symbols_urls,
                                      symbols_cache,
                                      symbols_tmp)) {
    usage();
    return 1;
  }

  Minidump minidump(argv[optind]);
  vector<string> symbol_paths;
  // allow symbol paths to be passed on the commandline.
  for (int i = optind + 1; i < argc; i++) {
    symbol_paths.push_back(argv[i]);
  }

  Minidump dump(argv[optind]);
  if (!dump.Read()) {
    error("Couldn't read minidump %s", argv[optind]);
  }

  scoped_ptr<SymbolSupplier> symbol_supplier;
  if (!symbols_urls.empty()) {
    vector<string> server_paths(symbols_urls.begin(), symbols_urls.end());
    symbol_supplier.reset(new HTTPSymbolSupplier(server_paths,
                                                 symbols_cache,
                                                 symbol_paths,
                                                 symbols_tmp));
  } else if (!symbol_paths.empty()) {
    symbol_supplier.reset(new SimpleSymbolSupplier(symbol_paths));
  }
  BasicSourceLineResolver resolver;

  SystemInfo system_info;
  MinidumpProcessor::GetCPUInfo(&dump, &system_info);
  MinidumpProcessor::GetOSInfo(&dump, &system_info);

  MinidumpModuleList *modules = dump.GetModuleList();
  MinidumpMemoryList* memory_list = dump.GetMemoryList();

  if (!modules || !memory_list) {
    error("Minidump %s is missing modules or memory_list", argv[1]);
  }

  // Default to top of the stack from the exception context
  MinidumpException* exception = dump.GetException();
  if (!exception)
    error("Minidump %s doesn't have an exception record!", argv[1]);

  MinidumpContext* context = exception->GetContext();
  if (!context)
    error("Minidump %s doesn't have an exception context!", argv[1]);

  uint64_t addr = GetStackPointer(context);


  MinidumpMemoryRegion* memory =
    memory_list->GetMemoryRegionForAddress(addr);
  if (!memory) {
    error("Minidump %s doesn't contain a memory region that contains "
          "address %s", argv[1], argv[3]);
  }

  int wordsize;
  if (system_info.cpu == "amd64") {
    wordsize = 8;
  }
  else {
    wordsize = 4;
  }
  u_int64_t memory_max = memory->GetBase() + memory->GetSize();
  for (int i = 0;
       addr < memory_max;
       i++, addr += wordsize) {
    StackFrame* frame = GetStackFrameCPU(system_info);
    if (frame == NULL) {
      error("Unknown CPU type");
    }
    if (wordsize == 4) {
      u_int32_t ip;
      memory->GetMemoryAtAddress(addr, &ip);
      frame->instruction = ip;
    }
    else {
      u_int64_t ip;
      memory->GetMemoryAtAddress(addr, &ip);
      frame->instruction = ip;
    }

    const CodeModule *module =
      modules->GetModuleForAddress(frame->instruction);
    if (module) {
      frame->module = module;
      if (!resolver.HasModule(frame->module)) {
        string symbol_file;
        char *symbol_data = NULL;
        size_t symbol_data_size = 0;
        SymbolSupplier::SymbolResult symbol_result =
          symbol_supplier->GetCStringSymbolData(module,
                                                &system_info,
                                                &symbol_file,
                                                &symbol_data,
                                                &symbol_data_size);

        switch (symbol_result) {
        case SymbolSupplier::FOUND:
          resolver.LoadModuleUsingMemoryBuffer(frame->module,
                                               symbol_data,
                                               symbol_data_size);
          break;
        case SymbolSupplier::NOT_FOUND:
          break;  // nothing to do
        case SymbolSupplier::INTERRUPT:
          return false;
        }
        // Inform symbol supplier to free the unused data memory buffer.
        if (resolver.ShouldDeleteMemoryBufferAfterLoadModule())
          symbol_supplier->FreeSymbolData(module);
      }
      resolver.FillSourceLineInfo(frame);
      if (!frame->function_name.empty() || show_all) {
        if (wordsize == 8) {
          printf("0x%016lx: ", addr);
        }
        else {
          printf("0x%08x: ", (u_int32_t)addr);
        }
        print_frame(frame);
      }
    }

    delete frame;
  }
  return 0;
}
