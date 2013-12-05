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
#include <fstream>
#include <iostream>
#include <ostream>
#include <vector>
#include <cstdlib>

#include <errno.h>
#include <getopt.h>
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
#include "google_breakpad/processor/stackwalker.h"
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
using google_breakpad::MinidumpMemoryInfo;
using google_breakpad::MinidumpMemoryInfoList;
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
using google_breakpad::Stackwalker;
using google_breakpad::SymbolSupplier;

using std::string;
using std::vector;
using std::ifstream;

namespace {

// If a thread contains more frames than this, frames will
// be truncated.
const unsigned kMaxThreadFrames = 100;

// If a thread's frames have been truncated, this many frames
// should be preserved at the end of the frame list.
const unsigned kTailFramesWhenTruncating = 10;

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

string FrameTrust(StackFrame::FrameTrust trust) {
  switch (trust) {
  case StackFrame::FRAME_TRUST_NONE:
    return "none";
  case StackFrame::FRAME_TRUST_SCAN:
    return "scan";
  case StackFrame::FRAME_TRUST_CFI_SCAN:
    return "cfi_scan";
  case StackFrame::FRAME_TRUST_FP:
    return "frame_pointer";
  case StackFrame::FRAME_TRUST_CFI:
    return "cfi";
  case StackFrame::FRAME_TRUST_CONTEXT:
    return "context";
  }

  return "none";
}

// ContainsModule checks whether a given |module| is in the vector
// |modules|.
bool ContainsModule(
    const vector<const CodeModule*> *modules,
    const CodeModule *module) {
  assert(modules);
  assert(module);
  vector<const CodeModule*>::const_iterator iter;
  for (iter = modules->begin(); iter != modules->end(); ++iter) {
    if (module->debug_file().compare((*iter)->debug_file()) == 0 &&
        module->debug_identifier().compare((*iter)->debug_identifier()) == 0) {
      return true;
    }
  }
  return false;
}

// If frame_limit is zero, output all frames, otherwise only
// output the first |frame_limit| frames.
// Return true if the stack was truncated, false otherwise.
bool ConvertStackToJSON(const ProcessState& process_state,
                        const CallStack *stack,
                        Json::Value& json_stack,
                        int frame_limit) {
  const vector<const CodeModule*>* modules_without_symbols =
    process_state.modules_without_symbols();
  const vector<const CodeModule*>* modules_with_corrupt_symbols =
    process_state.modules_with_corrupt_symbols();

  int frame_count = stack->frames()->size();
  if (frame_limit > 0)
    frame_count = std::min(frame_count, frame_limit);

  // Does this stack need truncation?
  bool truncate = frame_count > kMaxThreadFrames;
  int last_head_frame, first_tail_frame;
  if (truncate) {
    last_head_frame = kMaxThreadFrames - kTailFramesWhenTruncating - 1;
    first_tail_frame = frame_count - kTailFramesWhenTruncating;
  }
  for (int frame_index = 0; frame_index < frame_count; ++frame_index) {
    if (truncate && frame_index > last_head_frame &&
        frame_index < first_tail_frame)
      // Elide the frames in the middle.
      continue;
    const StackFrame *frame = stack->frames()->at(frame_index);
    Json::Value frame_data;
    frame_data["frame"] = frame_index;
    frame_data["trust"] = FrameTrust(frame->trust);
    if (frame->module) {
      if (ContainsModule(modules_without_symbols, frame->module)) {
        frame_data["missing_symbols"] = true;
      }
      if (ContainsModule(modules_with_corrupt_symbols, frame->module)) {
        frame_data["corrupt_symbols"] = true;
      }
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
  return truncate;
}

int ConvertModulesToJSON(const ProcessState& process_state,
                         Json::Value& json) {
  const CodeModules* modules = process_state.modules();
  const vector<const CodeModule*>* modules_without_symbols =
    process_state.modules_without_symbols();
  const vector<const CodeModule*>* modules_with_corrupt_symbols =
    process_state.modules_with_corrupt_symbols();
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
    if (ContainsModule(modules_without_symbols, module)) {
      module_data["missing_symbols"] = true;
    }
    if (ContainsModule(modules_with_corrupt_symbols, module)) {
      module_data["corrupt_symbols"] = true;
    }
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
  int main_module = ConvertModulesToJSON(process_state, modules);
  if (main_module != -1)
    root["main_module"] = main_module;
  root["modules"] = modules;

  Json::Value threads(Json::arrayValue);
  int thread_count = process_state.threads()->size();
  root["thread_count"] = thread_count;
  for (int thread_index = 0; thread_index < thread_count; ++thread_index) {
    Json::Value thread;
    Json::Value stack(Json::arrayValue);
    const CallStack* raw_stack = process_state.threads()->at(thread_index);
    if (ConvertStackToJSON(process_state, raw_stack, stack, 0)) {
      thread["frames_truncated"] = true;
      thread["total_frames"] =
        static_cast<Json::UInt>(raw_stack->frames()->size());
    }
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
    ConvertStackToJSON(process_state, crashing_stack, stack, 10);

    crashing_thread["threads_index"] = requesting_thread;
    crashing_thread["frames"] = stack;
    crashing_thread["total_frames"] =
      static_cast<Json::UInt>(crashing_stack->frames()->size());
    root["crashing_thread"] = crashing_thread;
  }

  // Exploitability rating
  root["sensitive"]["exploitability"] = ExploitabilityString(process_state.exploitability());
}

static void ConvertLargestFreeVMToJSON(Minidump& dump,
                                       Json::Value& raw_root,
                                       Json::Value& root)
{
  MinidumpMemoryInfoList* memory_info_list = dump.GetMemoryInfoList();
  if (!memory_info_list || !memory_info_list->valid()) {
    return;
  }

  uint64_t reserve_address =
    strtoull(raw_root.get("BreakpadReserveAddress", "0").asCString(), nullptr, 10);
  uint64_t reserve_size =
    strtoull(raw_root.get("BreakpadReserveSize", "0").asCString(), nullptr, 10);

  uint64_t largest_free_block = 0;

  for (int i = 0; i < memory_info_list->info_count(); ++i) {
    const MinidumpMemoryInfo* memory_info =
      memory_info_list->GetMemoryInfoAtIndex(i);
    if (!memory_info->valid()) {
      continue;
    }
    const MDRawMemoryInfo* raw_info = memory_info->info();
    if (raw_info->base_address >= reserve_address &&
        raw_info->base_address < reserve_address + reserve_size) {
      continue;
    }
    if (raw_info->state == MD_MEMORY_STATE_FREE &&
        raw_info->region_size > largest_free_block) {
      largest_free_block = raw_info->region_size;
    }
  }

  root["largest_free_vm_block"] = ToHex(largest_free_block);
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

//*** This code copy-pasted from minidump_stackwalk.cc ***

// Separator character for machine readable output.
static const char kOutputSeparator = '|';

// StripSeparator takes a string |original| and returns a copy
// of the string with all occurences of |kOutputSeparator| removed.
static string StripSeparator(const string &original) {
  string result = original;
  string::size_type position = 0;
  while ((position = result.find(kOutputSeparator, position)) != string::npos) {
    result.erase(position, 1);
  }
  position = 0;
  while ((position = result.find('\n', position)) != string::npos) {
    result.erase(position, 1);
  }
  return result;
}

// PrintStackMachineReadable prints the call stack in |stack| to stdout,
// in the following machine readable pipe-delimited text format:
// thread number|frame number|module|function|source file|line|offset
//
// Module, function, source file, and source line may all be empty
// depending on availability.  The code offset follows the same rules as
// PrintStack above.
static void PrintStackMachineReadable(int thread_num, const CallStack *stack) {
  int frame_count = stack->frames()->size();
  // Does this stack need truncation?
  bool truncate = frame_count > kMaxThreadFrames;
  int last_head_frame, first_tail_frame;
  if (truncate) {
    last_head_frame = kMaxThreadFrames - kTailFramesWhenTruncating - 1;
    first_tail_frame = frame_count - kTailFramesWhenTruncating;
  }
  for (int frame_index = 0; frame_index < frame_count; ++frame_index) {
    if (truncate && frame_index > last_head_frame &&
        frame_index < first_tail_frame)
      // Elide the frames in the middle.
      continue;

    const StackFrame *frame = stack->frames()->at(frame_index);
    printf("%d%c%d%c", thread_num, kOutputSeparator, frame_index,
           kOutputSeparator);

    uint64_t instruction_address = frame->ReturnAddress();

    if (frame->module) {
      assert(!frame->module->code_file().empty());
      printf("%s", StripSeparator(PathnameStripper::File(
                     frame->module->code_file())).c_str());
      if (!frame->function_name.empty()) {
        printf("%c%s", kOutputSeparator,
               StripSeparator(frame->function_name).c_str());
        if (!frame->source_file_name.empty()) {
          printf("%c%s%c%d%c0x%" PRIx64,
                 kOutputSeparator,
                 StripSeparator(frame->source_file_name).c_str(),
                 kOutputSeparator,
                 frame->source_line,
                 kOutputSeparator,
                 instruction_address - frame->source_line_base);
        } else {
          printf("%c%c%c0x%" PRIx64,
                 kOutputSeparator,  // empty source file
                 kOutputSeparator,  // empty source line
                 kOutputSeparator,
                 instruction_address - frame->function_base);
        }
      } else {
        printf("%c%c%c%c0x%" PRIx64,
               kOutputSeparator,  // empty function name
               kOutputSeparator,  // empty source file
               kOutputSeparator,  // empty source line
               kOutputSeparator,
               instruction_address - frame->module->base_address());
      }
    } else {
      // the printf before this prints a trailing separator for module name
      printf("%c%c%c%c0x%" PRIx64,
             kOutputSeparator,  // empty function name
             kOutputSeparator,  // empty source file
             kOutputSeparator,  // empty source line
             kOutputSeparator,
             instruction_address);
    }
    printf("\n");
  }
}

// PrintModulesMachineReadable outputs a list of loaded modules,
// one per line, in the following machine-readable pipe-delimited
// text format:
// Module|{Module Filename}|{Version}|{Debug Filename}|{Debug Identifier}|
// {Base Address}|{Max Address}|{Main}
static void PrintModulesMachineReadable(const CodeModules *modules) {
  if (!modules)
    return;

  uint64_t main_address = 0;
  const CodeModule *main_module = modules->GetMainModule();
  if (main_module) {
    main_address = main_module->base_address();
  }

  unsigned int module_count = modules->module_count();
  for (unsigned int module_sequence = 0;
       module_sequence < module_count;
       ++module_sequence) {
    const CodeModule *module = modules->GetModuleAtSequence(module_sequence);
    uint64_t base_address = module->base_address();
    printf("Module%c%s%c%s%c%s%c%s%c0x%08" PRIx64 "%c0x%08" PRIx64 "%c%d\n",
           kOutputSeparator,
           StripSeparator(PathnameStripper::File(module->code_file())).c_str(),
           kOutputSeparator, StripSeparator(module->version()).c_str(),
           kOutputSeparator,
           StripSeparator(PathnameStripper::File(module->debug_file())).c_str(),
           kOutputSeparator,
           StripSeparator(module->debug_identifier()).c_str(),
           kOutputSeparator, base_address,
           kOutputSeparator, base_address + module->size() - 1,
           kOutputSeparator,
           main_module != NULL && base_address == main_address ? 1 : 0);
  }
}

static void PrintProcessStateMachineReadable(const ProcessState& process_state)
{
  // Print OS and CPU information.
  // OS|{OS Name}|{OS Version}
  // CPU|{CPU Name}|{CPU Info}|{Number of CPUs}
  printf("OS%c%s%c%s\n", kOutputSeparator,
         StripSeparator(process_state.system_info()->os).c_str(),
         kOutputSeparator,
         StripSeparator(process_state.system_info()->os_version).c_str());
  printf("CPU%c%s%c%s%c%d\n", kOutputSeparator,
         StripSeparator(process_state.system_info()->cpu).c_str(),
         kOutputSeparator,
         // this may be empty
         StripSeparator(process_state.system_info()->cpu_info).c_str(),
         kOutputSeparator,
         process_state.system_info()->cpu_count);

  int requesting_thread = process_state.requesting_thread();

  // Print crash information.
  // Crash|{Crash Reason}|{Crash Address}|{Crashed Thread}
  printf("Crash%c", kOutputSeparator);
  if (process_state.crashed()) {
    printf("%s%c0x%" PRIx64 "%c",
           StripSeparator(process_state.crash_reason()).c_str(),
           kOutputSeparator, process_state.crash_address(), kOutputSeparator);
  } else {
    // print assertion info, if available, in place of crash reason,
    // instead of the unhelpful "No crash"
    string assertion = process_state.assertion();
    if (!assertion.empty()) {
      printf("%s%c%c", StripSeparator(assertion).c_str(),
             kOutputSeparator, kOutputSeparator);
    } else {
      printf("No crash%c%c", kOutputSeparator, kOutputSeparator);
    }
  }

  if (requesting_thread != -1) {
    printf("%d\n", requesting_thread);
  } else {
    printf("\n");
  }

  PrintModulesMachineReadable(process_state.modules());

  // blank line to indicate start of threads
  printf("\n");

  // If the thread that requested the dump is known, print it first.
  if (requesting_thread != -1) {
    PrintStackMachineReadable(requesting_thread,
                              process_state.threads()->at(requesting_thread));
  }

  // Print all of the threads in the dump.
  int thread_count = process_state.threads()->size();
  for (int thread_index = 0; thread_index < thread_count; ++thread_index) {
    if (thread_index != requesting_thread) {
      // Don't print the crash thread again, it was already printed.
      PrintStackMachineReadable(thread_index,
                                process_state.threads()->at(thread_index));
    }
  }
}

//*** End of copy-paste from minidump_stackwalk.cc ***

void usage() {
  fprintf(stderr, "Usage: stackwalker [options] <minidump> [<symbol paths]\n");
  fprintf(stderr, "Options:\n");
  fprintf(stderr, "\t--pretty\tPretty-print JSON output.\n");
  fprintf(stderr, "\t--pipe-dump\tProduce pipe-delimited output in addition to JSON output\n");
  fprintf(stderr, "\t--raw-json\tAn input file with the raw annotations as JSON\n");
  fprintf(stderr, "\t--help\tDisplay this help text.\n");
}

} // namespace
int main(int argc, char** argv)
{
  bool pretty = false;
  bool pipe = false;
  char* json_path = nullptr;
  static struct option long_options[] = {
    {"pretty", no_argument, nullptr, 'p'},
    {"pipe-dump", no_argument, nullptr, 'i'},
    {"raw-json", required_argument, nullptr, 'r'},
    {"help", no_argument, nullptr, 'h'},
    {nullptr, 0, nullptr, 0}
  };
  int arg;
  int option_index = 0;
  while((arg = getopt_long(argc, argv, "", long_options, &option_index))
        != -1) {
    switch(arg) {
    case 0:
      if (long_options[option_index].flag != 0)
          break;
      break;
    case 'p':
      pretty = true;
      break;
    case 'i':
      pipe = true;
      break;
    case 'r':
      json_path = optarg;
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

  Minidump minidump(argv[optind]);
  vector<string> symbol_paths;
  // allow symbol paths to be passed on the commandline.
  for (int i = optind + 1; i < argc; i++) {
    symbol_paths.push_back(argv[i]);
  }

  minidump.Read();
  // process minidump
  Stackwalker::set_max_frames(UINT32_MAX);
  Json::Value root;
  SimpleSymbolSupplier symbol_supplier(symbol_paths);
  BasicSourceLineResolver resolver;
  MinidumpProcessor minidump_processor(&symbol_supplier, &resolver, true);
  ProcessState process_state;
  ProcessResult result =
    minidump_processor.Process(&minidump, &process_state);

  if (pipe) {
    if (result == google_breakpad::PROCESS_OK) {
      PrintProcessStateMachineReadable(process_state);
    }
    printf("====PIPE DUMP ENDS===\n");
  }

  Json::Value raw_root(Json::objectValue);
  if (json_path) {
    Json::Reader reader;
    ifstream raw_stream(json_path);
    reader.parse(raw_stream, raw_root);
  }

  root["status"] = ResultString(result);
  root["sensitive"] = Json::Value(Json::objectValue);
  if (result == google_breakpad::PROCESS_OK) {
    ConvertProcessStateToJSON(process_state, root);
  }
  ConvertLargestFreeVMToJSON(minidump, raw_root, root);
  Json::Writer* writer;
  if (pretty)
    writer = new Json::StyledWriter();
  else
    writer = new Json::FastWriter();
  printf("%s\n", writer->write(root).c_str());

  delete writer;
  return 0;
}
