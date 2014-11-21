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
#include <set>
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
#include "google_breakpad/processor/stack_frame_symbolizer.h"
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
using google_breakpad::StackFrameAMD64;
using google_breakpad::StackFrameARM;
using google_breakpad::StackFrameARM64;
using google_breakpad::StackFrameMIPS;
using google_breakpad::StackFramePPC;
using google_breakpad::StackFrameSPARC;
using google_breakpad::StackFrameX86;

using google_breakpad::StackFrameSymbolizer;
using google_breakpad::Stackwalker;
using google_breakpad::SymbolSupplier;
using google_breakpad::SystemInfo;

using std::string;
using std::vector;
using std::ifstream;

#if (__GNUC__ == 4) && (__GNUC_MINOR__ < 6)
#define nullptr __null
#endif

namespace {

// If a thread contains more frames than this, frames will
// be truncated.
const unsigned kMaxThreadFrames = 100;

// If a thread's frames have been truncated, this many frames
// should be preserved at the end of the frame list.
const unsigned kTailFramesWhenTruncating = 10;

static string ToHex(uint64_t value) {
  char buffer[17];
  sprintf(buffer, "0x%lx", value);
  return buffer;
}

static string ToInt(uint64_t value) {
  char buffer[17];
  sprintf(buffer, "%ld", value);
  return buffer;
}

class StackFrameSymbolizerForward : public StackFrameSymbolizer {
public:
  StackFrameSymbolizerForward(SymbolSupplier* supplier,
                              SourceLineResolverInterface* resolver)
    : StackFrameSymbolizer(supplier, resolver) {}

  virtual SymbolizerResult FillSourceLineInfo(const CodeModules* modules,
                                              const SystemInfo* system_info,
                                              StackFrame* stack_frame) {
    SymbolizerResult res =
      StackFrameSymbolizer::FillSourceLineInfo(modules,
                                               system_info,
                                               stack_frame);
    RecordResult(stack_frame->module, res);
    return res;
  }

  bool SymbolsLoadedFor(const CodeModule* module) const {
    return loaded_modules_.find(module) != loaded_modules_.end();
  }

private:
  void RecordResult(const CodeModule* module, SymbolizerResult result) {
    if (result == SymbolizerResult::kNoError && !SymbolsLoadedFor(module)) {
      loaded_modules_.insert(module);
    }
  }
  std::set<const CodeModule*> loaded_modules_;
};

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
  case StackFrame::FRAME_TRUST_PREWALKED:
    return "prewalked";
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

void AddRegister(Json::Value& registers, const char* reg,
                 uint32_t value) {
  char buf[11];
  snprintf(buf, sizeof(buf), "0x%08x", value);
  registers[reg] = buf;
}

void AddRegister(Json::Value& registers, const char* reg,
                 uint64_t value) {
  char buf[19];
  snprintf(buf, sizeof(buf), "0x%016lx", value);
  registers[reg] = buf;
}

// Save all the registers from |frame| of CPU type |cpu|
// into keys in |registers|.
void RegistersToJSON(const StackFrame* frame,
                     const string& cpu,
                     Json::Value& registers) {
  if (cpu == "x86") {
    const StackFrameX86 *frame_x86 =
      reinterpret_cast<const StackFrameX86*>(frame);

    if (frame_x86->context_validity & StackFrameX86::CONTEXT_VALID_EIP)
      AddRegister(registers, "eip", frame_x86->context.eip);
    if (frame_x86->context_validity & StackFrameX86::CONTEXT_VALID_ESP)
      AddRegister(registers, "esp", frame_x86->context.esp);
    if (frame_x86->context_validity & StackFrameX86::CONTEXT_VALID_EBP)
      AddRegister(registers, "ebp", frame_x86->context.ebp);
    if (frame_x86->context_validity & StackFrameX86::CONTEXT_VALID_EBX)
      AddRegister(registers, "ebx", frame_x86->context.ebx);
    if (frame_x86->context_validity & StackFrameX86::CONTEXT_VALID_ESI)
      AddRegister(registers, "esi", frame_x86->context.esi);
    if (frame_x86->context_validity & StackFrameX86::CONTEXT_VALID_EDI)
      AddRegister(registers, "edi", frame_x86->context.edi);
    if (frame_x86->context_validity == StackFrameX86::CONTEXT_VALID_ALL) {
      AddRegister(registers, "eax", frame_x86->context.eax);
      AddRegister(registers, "ecx", frame_x86->context.ecx);
      AddRegister(registers, "edx", frame_x86->context.edx);
      AddRegister(registers, "efl", frame_x86->context.eflags);
    }
  } else if (cpu == "ppc") {
    const StackFramePPC *frame_ppc =
      reinterpret_cast<const StackFramePPC*>(frame);

    if (frame_ppc->context_validity & StackFramePPC::CONTEXT_VALID_SRR0)
      AddRegister(registers, "srr0", frame_ppc->context.srr0);
    if (frame_ppc->context_validity & StackFramePPC::CONTEXT_VALID_GPR1)
      AddRegister(registers, "r1", frame_ppc->context.gpr[1]);
  } else if (cpu == "amd64") {
    const StackFrameAMD64 *frame_amd64 =
      reinterpret_cast<const StackFrameAMD64*>(frame);

    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RAX)
      AddRegister(registers, "rax", frame_amd64->context.rax);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RDX)
      AddRegister(registers, "rdx", frame_amd64->context.rdx);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RCX)
      AddRegister(registers, "rcx", frame_amd64->context.rcx);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RBX)
      AddRegister(registers, "rbx", frame_amd64->context.rbx);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RSI)
      AddRegister(registers, "rsi", frame_amd64->context.rsi);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RDI)
      AddRegister(registers, "rdi", frame_amd64->context.rdi);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RBP)
      AddRegister(registers, "rbp", frame_amd64->context.rbp);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RSP)
      AddRegister(registers, "rsp", frame_amd64->context.rsp);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R8)
      AddRegister(registers, "r8", frame_amd64->context.r8);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R9)
      AddRegister(registers, "r9", frame_amd64->context.r9);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R10)
      AddRegister(registers, "r10", frame_amd64->context.r10);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R11)
      AddRegister(registers, "r11", frame_amd64->context.r11);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R12)
      AddRegister(registers, "r12", frame_amd64->context.r12);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R13)
      AddRegister(registers, "r13", frame_amd64->context.r13);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R14)
      AddRegister(registers, "r14", frame_amd64->context.r14);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_R15)
      AddRegister(registers, "r15", frame_amd64->context.r15);
    if (frame_amd64->context_validity & StackFrameAMD64::CONTEXT_VALID_RIP)
      AddRegister(registers, "rip", frame_amd64->context.rip);
  } else if (cpu == "sparc") {
    const StackFrameSPARC *frame_sparc =
      reinterpret_cast<const StackFrameSPARC*>(frame);

    if (frame_sparc->context_validity & StackFrameSPARC::CONTEXT_VALID_SP)
      AddRegister(registers, "sp", frame_sparc->context.g_r[14]);
    if (frame_sparc->context_validity & StackFrameSPARC::CONTEXT_VALID_FP)
      AddRegister(registers, "fp", frame_sparc->context.g_r[30]);
    if (frame_sparc->context_validity & StackFrameSPARC::CONTEXT_VALID_PC)
      AddRegister(registers, "pc", frame_sparc->context.pc);
  } else if (cpu == "arm") {
    const StackFrameARM *frame_arm =
      reinterpret_cast<const StackFrameARM*>(frame);

    // Argument registers (caller-saves), which will likely only be valid
    // for the youngest frame.
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R0)
      AddRegister(registers, "r0", frame_arm->context.iregs[0]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R1)
      AddRegister(registers, "r1", frame_arm->context.iregs[1]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R2)
      AddRegister(registers, "r2", frame_arm->context.iregs[2]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R3)
      AddRegister(registers, "r3", frame_arm->context.iregs[3]);

    // General-purpose callee-saves registers.
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R4)
      AddRegister(registers, "r4", frame_arm->context.iregs[4]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R5)
      AddRegister(registers, "r5", frame_arm->context.iregs[5]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R6)
      AddRegister(registers, "r6", frame_arm->context.iregs[6]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R7)
      AddRegister(registers, "r7", frame_arm->context.iregs[7]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R8)
      AddRegister(registers, "r8", frame_arm->context.iregs[8]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R9)
      AddRegister(registers, "r9", frame_arm->context.iregs[9]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R10)
      AddRegister(registers, "r10", frame_arm->context.iregs[10]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_R12)
      AddRegister(registers, "r12", frame_arm->context.iregs[12]);

    // Registers with a dedicated or conventional purpose.
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_FP)
      AddRegister(registers, "fp", frame_arm->context.iregs[11]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_SP)
      AddRegister(registers, "sp", frame_arm->context.iregs[13]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_LR)
      AddRegister(registers, "lr", frame_arm->context.iregs[14]);
    if (frame_arm->context_validity & StackFrameARM::CONTEXT_VALID_PC)
      AddRegister(registers, "pc", frame_arm->context.iregs[15]);
  } else if (cpu == "arm64") {
    const StackFrameARM64 *frame_arm64 =
      reinterpret_cast<const StackFrameARM64*>(frame);

    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X0) {
      AddRegister(registers, "x0", frame_arm64->context.iregs[0]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X1) {
      AddRegister(registers, "x1", frame_arm64->context.iregs[1]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X2) {
      AddRegister(registers, "x2", frame_arm64->context.iregs[2]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X3) {
      AddRegister(registers, "x3", frame_arm64->context.iregs[3]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X4) {
      AddRegister(registers, "x4", frame_arm64->context.iregs[4]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X5) {
      AddRegister(registers, "x5", frame_arm64->context.iregs[5]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X6) {
      AddRegister(registers, "x6", frame_arm64->context.iregs[6]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X7) {
      AddRegister(registers, "x7", frame_arm64->context.iregs[7]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X8) {
      AddRegister(registers, "x8", frame_arm64->context.iregs[8]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X9) {
      AddRegister(registers, "x9", frame_arm64->context.iregs[9]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X10) {
      AddRegister(registers, "x10", frame_arm64->context.iregs[10]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X11) {
      AddRegister(registers, "x11", frame_arm64->context.iregs[11]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X12) {
      AddRegister(registers, "x12", frame_arm64->context.iregs[12]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X13) {
      AddRegister(registers, "x13", frame_arm64->context.iregs[13]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X14) {
      AddRegister(registers, "x14", frame_arm64->context.iregs[14]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X15) {
      AddRegister(registers, "x15", frame_arm64->context.iregs[15]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X16) {
      AddRegister(registers, "x16", frame_arm64->context.iregs[16]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X17) {
      AddRegister(registers, "x17", frame_arm64->context.iregs[17]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X18) {
      AddRegister(registers, "x18", frame_arm64->context.iregs[18]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X19) {
      AddRegister(registers, "x19", frame_arm64->context.iregs[19]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X20) {
      AddRegister(registers, "x20", frame_arm64->context.iregs[20]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X21) {
      AddRegister(registers, "x21", frame_arm64->context.iregs[21]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X22) {
      AddRegister(registers, "x22", frame_arm64->context.iregs[22]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X23) {
      AddRegister(registers, "x23", frame_arm64->context.iregs[23]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X24) {
      AddRegister(registers, "x24", frame_arm64->context.iregs[24]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X25) {
      AddRegister(registers, "x25", frame_arm64->context.iregs[25]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X26) {
      AddRegister(registers, "x26", frame_arm64->context.iregs[26]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X27) {
      AddRegister(registers, "x27", frame_arm64->context.iregs[27]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_X28) {
      AddRegister(registers, "x28", frame_arm64->context.iregs[28]);
    }

    // Registers with a dedicated or conventional purpose.
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_FP) {
      AddRegister(registers, "fp", frame_arm64->context.iregs[29]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_LR) {
      AddRegister(registers, "lr", frame_arm64->context.iregs[30]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_SP) {
      AddRegister(registers, "sp", frame_arm64->context.iregs[31]);
    }
    if (frame_arm64->context_validity & StackFrameARM64::CONTEXT_VALID_PC) {
      AddRegister(registers, "pc", frame_arm64->context.iregs[32]);
    }
  } else if (cpu == "mips") {
    const StackFrameMIPS* frame_mips =
      reinterpret_cast<const StackFrameMIPS*>(frame);

    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_GP)
      AddRegister(registers, "gp", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_GP]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_SP)
      AddRegister(registers, "sp", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_SP]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_FP)
      AddRegister(registers, "fp", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_FP]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_RA)
      AddRegister(registers, "ra", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_RA]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_PC)
      AddRegister(registers, "pc", frame_mips->context.epc);

    // Save registers s0-s7
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S0)
      AddRegister(registers, "s0", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S0]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S1)
      AddRegister(registers, "s1", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S1]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S2)
      AddRegister(registers, "s2", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S2]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S3)
      AddRegister(registers, "s3", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S3]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S4)
      AddRegister(registers, "s4", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S4]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S5)
      AddRegister(registers, "s5", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S5]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S6)
      AddRegister(registers, "s6", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S6]);
    if (frame_mips->context_validity & StackFrameMIPS::CONTEXT_VALID_S7)
      AddRegister(registers, "s7", frame_mips->context.iregs[MD_CONTEXT_MIPS_REG_S7]);
  }
}

// If frame_limit is zero, output all frames, otherwise only
// output the first |frame_limit| frames.
// If |save_initial_registers| is true, the first frame in the stack
// will have its register state stored in a "registers" key.
// Return true if the stack was truncated, false otherwise.
bool ConvertStackToJSON(const ProcessState& process_state,
                        const CallStack *stack,
                        Json::Value& json_stack,
                        int frame_limit,
                        bool save_initial_registers) {
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
    if (frame_index == 0 && save_initial_registers) {
      Json::Value registers;
      RegistersToJSON(frame, process_state.system_info()->cpu, registers);
      frame_data["registers"] = registers;
    }

    json_stack.append(frame_data);
  }
  return truncate;
}

int ConvertModulesToJSON(const ProcessState& process_state,
                         const StackFrameSymbolizerForward& symbolizer,
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
    if (symbolizer.SymbolsLoadedFor(module)) {
      module_data["loaded_symbols"] = true;
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
                                      const StackFrameSymbolizerForward& symbolizer,
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
  int main_module = ConvertModulesToJSON(process_state, symbolizer, modules);
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
    if (ConvertStackToJSON(process_state, raw_stack, stack, 0, false)) {
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
    ConvertStackToJSON(process_state, crashing_stack, stack, 10, true);

    crashing_thread["threads_index"] = requesting_thread;
    crashing_thread["frames"] = stack;
    crashing_thread["total_frames"] =
      static_cast<Json::UInt>(crashing_stack->frames()->size());
    root["crashing_thread"] = crashing_thread;
  }

  // Exploitability rating
  root["sensitive"]["exploitability"] = ExploitabilityString(process_state.exploitability());
}

static void ConvertMemoryInfoToJSON(Minidump& dump,
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
  uint64_t write_combine_size = 0;
  uint64_t tiny_block_size = 0;

  for (int i = 0; i < memory_info_list->info_count(); ++i) {
    const MinidumpMemoryInfo* memory_info =
      memory_info_list->GetMemoryInfoAtIndex(i);
    if (!memory_info->valid()) {
      continue;
    }
    const MDRawMemoryInfo* raw_info = memory_info->info();

    if (raw_info->state == MD_MEMORY_STATE_COMMIT &&
        raw_info->protection & MD_MEMORY_PROTECT_WRITECOMBINE) {
      write_combine_size += raw_info->region_size;
    }

    if (raw_info->state == MD_MEMORY_STATE_FREE &&
        // Minimum block size required by jemalloc and JS allocator
        raw_info->region_size < 0x100000) {
      tiny_block_size += raw_info->region_size;
    }

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
  root["write_combine_size"] = ToInt(write_combine_size);
  root["tiny_block_size"] = ToInt(tiny_block_size);

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
  // bug 950710 - Bad symbol files are causing the stackwalker to
  // run amok. Disabling this until we get an upstream fix.
  //Stackwalker::set_max_frames(UINT32_MAX);
  Json::Value root;
  SimpleSymbolSupplier symbol_supplier(symbol_paths);
  BasicSourceLineResolver resolver;
  StackFrameSymbolizerForward symbolizer(&symbol_supplier, &resolver);
  MinidumpProcessor minidump_processor(&symbolizer, true);
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
    ConvertProcessStateToJSON(process_state, symbolizer, root);
  }
  ConvertMemoryInfoToJSON(minidump, raw_root, root);
  Json::Writer* writer;
  if (pretty)
    writer = new Json::StyledWriter();
  else
    writer = new Json::FastWriter();
  printf("%s\n", writer->write(root).c_str());

  delete writer;
  exit(0);
}
