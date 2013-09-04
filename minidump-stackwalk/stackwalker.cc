// Copyright (c) 2011 The Mozilla Foundation.
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

// stackwalker produces a JSON-formatted representation of the
// contents of a minidump, including a stack trace per-thread.

#include <algorithm>
#include <iostream>
#include <ostream>
#include <vector>

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "google_breakpad/common/breakpad_types.h"
#include "google_breakpad/processor/basic_source_line_resolver.h"
#include "google_breakpad/processor/call_stack.h"
#include "google_breakpad/processor/code_module.h"
#include "google_breakpad/processor/code_modules.h"
#include "google_breakpad/processor/minidump.h"
#include "google_breakpad/processor/minidump_processor.h"
#include "google_breakpad/processor/process_state.h"
#include "google_breakpad/processor/stack_frame_cpu.h"
#include "processor/pathname_stripper.h"
#include "processor/simple_symbol_supplier.h"

#include "json/json.h"

using google_breakpad::BasicSourceLineResolver;
using google_breakpad::CallStack;
using google_breakpad::CodeModule;
using google_breakpad::CodeModules;
using google_breakpad::ExploitabilityRating;
using google_breakpad::Minidump;
using google_breakpad::MinidumpModule;
using google_breakpad::MinidumpProcessor;
using google_breakpad::PathnameStripper;
using google_breakpad::ProcessResult;
using google_breakpad::ProcessState;
using google_breakpad::SimpleSymbolSupplier;
using google_breakpad::SourceLineResolverInterface;
using google_breakpad::StackFrame;
using google_breakpad::StackFramePPC;
using google_breakpad::StackFrameSPARC;
using google_breakpad::StackFrameX86;
using google_breakpad::StackFrameAMD64;
using google_breakpad::SymbolSupplier;

using std::string;
using std::vector;

namespace {

static string ToHex(u_int64_t value) {
  char buffer[17];
  sprintf(buffer, "0x%lx", value);
  return buffer;
}

static string ToInt(int value) {
  char buffer[17];
  sprintf(buffer, "%d", value);
  return buffer;
}

// If frame_limit is zero, output all frames, otherwise only
// output the first |frame_limit| frames.
static void ConvertStackToJSON(const CallStack *stack,
                               Json::Value& json_stack,
                               int frame_limit) {
  int frame_count = stack->frames()->size();
  if (frame_limit > 0)
    frame_count = std::min(frame_count, frame_limit);
  for (int frame_index = 0; frame_index < frame_count; ++frame_index) {
    const StackFrame *frame = stack->frames()->at(frame_index);
    Json::Value frame_data;
    frame_data["frame"] = frame_index;
    if (frame->module) {
      assert(!frame->module->code_file().empty());
      frame_data["module"] = PathnameStripper::File(frame->module->code_file());

      if (!frame->function_name.empty()) {
        frame_data["function"] = frame->function_name;
        frame_data["function_offset"] = ToHex(frame->instruction
                                          - frame->function_base);
      }
      frame_data["module_offset"] = ToHex(frame->instruction
                                          - frame->module->base_address());

      if (!frame->source_file_name.empty()) {
        frame_data["file"] = frame->source_file_name;
        frame_data["line"] = frame->source_line;
      }
    }
    frame_data["offset"] = ToHex(frame->instruction);

    json_stack.append(frame_data);
  }
}

static int ConvertModulesToJSON(const CodeModules *modules,
                                Json::Value& json) {
  if (!modules)
    return -1;

  u_int64_t main_address = 0;
  const CodeModule *main_module = modules->GetMainModule();
  if (main_module) {
    main_address = main_module->base_address();
  }

  unsigned int module_count = modules->module_count();
  int main_module_index = -1;
  for (unsigned int module_sequence = 0;
       module_sequence < module_count;
       ++module_sequence) {
    const CodeModule *module = modules->GetModuleAtSequence(module_sequence);
    if (module->base_address() == main_address)
      main_module_index = module_sequence;

    Json::Value module_data;
    module_data["filename"] = PathnameStripper::File(module->code_file());
    module_data["version"] = module->version();
    module_data["debug_file"] = PathnameStripper::File(module->debug_file());
    module_data["debug_id"] = module->debug_identifier();
    module_data["base_addr"] = ToHex(module->base_address());
    module_data["end_addr"] = ToHex(module->base_address() + module->size());
    json.append(module_data);
  }
  return main_module_index;
}

static string ExploitabilityString(ExploitabilityRating exploitability) {
  string str;
  switch (exploitability) {
  case google_breakpad::EXPLOITABILITY_NOT_ANALYZED:
    str = "ERROR: dump not analyzed";
    break;
  case google_breakpad::EXPLOITABILITY_ERR_NOENGINE:
    str = "ERROR: unable to analyze dump";
    break;
  case google_breakpad::EXPLOITABILITY_ERR_PROCESSING:
    str = "ERROR: something went wrong";
    break;
  case google_breakpad::EXPLOITABILITY_NONE:
    str = "none";
    break;
  case google_breakpad::EXPLOITABILITY_INTERESTING:
    str = "interesting";
    break;
  case google_breakpad::EXPLOITABILITY_LOW:
    str = "low";
    break;
  case google_breakpad::EXPLOITABLITY_MEDIUM:
    str = "medium";
    break;
  case google_breakpad::EXPLOITABILITY_HIGH:
    str = "high";
    break;
  }
  return str;
}

static void ConvertProcessStateToJSON(const ProcessState& process_state,
                                      Json::Value& root) {
  // OS and CPU information.
  Json::Value system_info;
  system_info["os"] = process_state.system_info()->os;
  system_info["os_ver"] = process_state.system_info()->os_version;
  system_info["cpu_arch"] = process_state.system_info()->cpu;
  system_info["cpu_info"] = process_state.system_info()->cpu_info;
  system_info["cpu_count"] = process_state.system_info()->cpu_count;
  root["system_info"] = system_info;

  // Crash info
  Json::Value crash_info;
  int requesting_thread = process_state.requesting_thread();
  if (process_state.crashed()) {
    crash_info["type"] = process_state.crash_reason();
    crash_info["address"] = ToHex(process_state.crash_address());
    if (requesting_thread != -1) {
      crash_info["crashing_thread"] = requesting_thread;
    }
  } else {
    crash_info["type"] = Json::Value(Json::nullValue);
    // Add assertion info, if available
    string assertion = process_state.assertion();
    if (!assertion.empty()) {
      crash_info["assertion"] = assertion;
    }
  }
  root["crash_info"] = crash_info;

  Json::Value modules(Json::arrayValue);
  int main_module = ConvertModulesToJSON(process_state.modules(), modules);
  if (main_module != -1)
    root["main_module"] = main_module;
  root["modules"] = modules;

  Json::Value threads(Json::arrayValue);
  int thread_count = process_state.threads()->size();
  root["thread_count"] = thread_count;
  for (int thread_index = 0; thread_index < thread_count; ++thread_index) {
    Json::Value thread;
    Json::Value stack(Json::arrayValue);
    ConvertStackToJSON(process_state.threads()->at(thread_index),
                       stack, 0);
    thread["frames"] = stack;
    thread["frame_count"] = stack.size();
    threads.append(thread);
  }
  root["threads"] = threads;

  // Put the first ten frames of the crashing thread in a separate field
  // for ease of searching.
  if (process_state.crashed() && requesting_thread != -1) {
    Json::Value crashing_thread;
    Json::Value stack;
    const CallStack *crashing_stack =
      process_state.threads()->at(requesting_thread);
    ConvertStackToJSON(crashing_stack, stack, 10);

    crashing_thread["threads_index"] = requesting_thread;
    crashing_thread["frames"] = stack;
    crashing_thread["total_frames"] =
      static_cast<Json::UInt>(crashing_stack->frames()->size());
    root["crashing_thread"] = crashing_thread;
  }

  // Exploitability rating
  root["sensitive"]["exploitability"] = ExploitabilityString(process_state.exploitability());
}

static string ResultString(ProcessResult result) {
  string str;
  switch (result) {
  case google_breakpad::PROCESS_OK:
    str = "OK";
    break;
  case google_breakpad::PROCESS_ERROR_MINIDUMP_NOT_FOUND:
    str = "ERROR_MINIDUMP_NOT_FOUND";
    break;
  case google_breakpad::PROCESS_ERROR_NO_MINIDUMP_HEADER:
    str = "ERROR_NO_MINIDUMP_HEADER";
    break;
  case google_breakpad::PROCESS_ERROR_NO_THREAD_LIST:
    str = "ERROR_NO_THREAD_LIST";
    break;
  case google_breakpad::PROCESS_ERROR_GETTING_THREAD:
    str = "ERROR_GETTING_THREAD";
    break;
  case google_breakpad::PROCESS_ERROR_GETTING_THREAD_ID:
    str = "ERROR_GETTING_THREAD_ID";
    break;
  case google_breakpad::PROCESS_ERROR_DUPLICATE_REQUESTING_THREADS:
    str = "ERROR_DUPLICATE_REQUESTING_THREADS";
    break;
  case google_breakpad::PROCESS_SYMBOL_SUPPLIER_INTERRUPTED:
    str = "SYMBOL_SUPPLIER_INTERRUPTED";
    break;
  }
  return str;
}

} // namespace
int main(int argc, char** argv)
{
  bool pretty = false;
  int arg;
  while((arg = getopt(argc, argv, "p")) != -1) {
    switch(arg) {
    case 'p':
      pretty = true;
      break;
    case '?':
      fprintf(stderr, "Option -%c requires an argument\n", (char)optopt);
      break;
    default:
      fprintf(stderr, "Unknown option: -%c\n", (char)arg);
      return 1;
    }
  }

  if (optind >= argc) {
    fprintf(stderr, "Usage: stackwalker [-p] <minidump> [<symbol paths]\n");
    return 1;
  }

  Minidump minidump(argv[optind]);
  vector<string> symbol_paths;
  // allow symbol paths to be passed on the commandline.
  for (int i = optind + 1; i < argc; i++) {
    symbol_paths.push_back(argv[i]);
  }

  minidump.Read();
  // process minidump
  Json::Value root;
  SimpleSymbolSupplier symbol_supplier(symbol_paths);
  BasicSourceLineResolver resolver;
  MinidumpProcessor minidump_processor(&symbol_supplier, &resolver, true);
  ProcessState process_state;
  ProcessResult result =
    minidump_processor.Process(&minidump, &process_state);

  root["status"] = ResultString(result);
  root["sensitive"] = Json::Value(Json::objectValue);
  if (result == google_breakpad::PROCESS_OK) {
    ConvertProcessStateToJSON(process_state, root);
  }
  Json::Writer* writer;
  if (pretty) 
    writer = new Json::StyledWriter();
  else
    writer = new Json::FastWriter();
  printf("%s\n", writer->write(root).c_str());

  delete writer;
  return 0;
}
