// vim: set ts=2 sw=2 tw=99 et:
// Copyright (c) 2011 The Mozilla Foundation
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

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "google_breakpad/processor/minidump.h"
#include "processor/disassembler_x86.h"
#include "third_party/libdisasm/libdis.h"

using namespace google_breakpad;

#define ERROR_MAP(_)                \
  _(UNKNOWN)                        \
  _(CORRUPT_CODE)                   \
  _(EIP_IN_BETWEEN)                 \
  _(BAD_BRANCH_TARGET)              \
  _(BAD_EIP_INSTRUCTION)            \

enum CrashError {
#define M(n) CRASH_##n,
  ERROR_MAP(M)
#undef M
  CRASH_REASONS
};

const char *CrashReasons[] =
{
#define M(n) #n,
  ERROR_MAP(M)
#undef M
  NULL
};

void error()
{
  printf("ERROR\n");
  exit(1);
}

static void
DumpStream(const u_int8_t *bytes, size_t size)
{
  for (size_t i = 0; i < size; i++) {
    if (i % 16 == 0)
      printf("%04lX: ", i);
    printf("%02x ", bytes[i]);
    if (i % 16 == 15)
      printf("\n");
  }
}

struct DisRegion {
  DisRegion(CrashError error, u_int32_t bytes) : error(error), bytes(bytes)
  { }
  CrashError error;
  u_int32_t bytes;
};

static DisRegion
AnalyzeCodeRegion(DisassemblerX86 &dis, u_int32_t limit, u_int64_t start, u_int64_t ip);

int main(int argc, char** argv)
{
  if (argc != 2) {
    fprintf(stderr, "Usage: %s <minidump>\n", argv[0]);
    exit(1);
  }

  Minidump minidump(argv[1]);
  if (!minidump.Read()) {
    error();
  }

  MinidumpException* exception = minidump.GetException();
  MinidumpMemoryList* memory_list = minidump.GetMemoryList();
  MinidumpMemoryInfoList* memory_info_list = minidump.GetMemoryInfoList();
  if (!exception) {
    error();
  }
  if (!memory_list) {
    error();
  }
  if (!memory_info_list) {
    // This happens on all pre-Win7 dumps, and possibly others (corruption?)
    printf("MEMORY_INFO_NOT_PRESENT\n");
    return 0;
  }

  MinidumpContext* context = exception->GetContext();
  if (!context) {
    error();
  }

  u_int64_t instruction_pointer;
  switch (context->GetContextCPU()) {
  case MD_CONTEXT_X86:
    instruction_pointer = context->GetContextX86()->eip;
    break;
  case MD_CONTEXT_AMD64:
    instruction_pointer = context->GetContextAMD64()->rip;
    break;
  case MD_CONTEXT_ARM:
    instruction_pointer = context->GetContextARM()->iregs[15];
    break;
  default:
    error();
    break;
  }

  const MinidumpMemoryInfo* info =
    memory_info_list->GetMemoryInfoForAddress(instruction_pointer);
  if (!info) {
    printf("INSTRUCTION_POINTER_IN_INACCESSIBLE_MEM\n");
    return 0;
  }

  const MDRawMemoryInfo* raw_info = info->info();
  if (raw_info->state == MD_MEMORY_STATE_FREE ||
      (raw_info->protection & MD_MEMORY_PROTECTION_ACCESS_MASK) == MD_MEMORY_PROTECT_NOACCESS) {
    printf("INSTRUCTION_POINTER_IN_INACCESSIBLE_MEM\n");
    return 0;
  }

  // These flags are mutually exclusive, so we have to check them all
  const int executable_flags = MD_MEMORY_PROTECT_EXECUTE | MD_MEMORY_PROTECT_EXECUTE_READ |
    MD_MEMORY_PROTECT_EXECUTE_READWRITE | MD_MEMORY_PROTECT_EXECUTE_WRITECOPY;
  if (!(raw_info->protection & executable_flags)) {
    printf("INSTRUCTION_POINTER_NOT_EXECUTABLE\n");
    return 0;
  }

  if (raw_info->region_size != 0x10000) {
    printf("NOT_JIT_CODE\n");
    return 0;
  }

  if (raw_info->type & MD_MEMORY_TYPE_IMAGE) {
    printf("NOT_JIT_CODE\n");
    return 0;
  }

  MinidumpMemoryRegion* region =
    memory_list->GetMemoryRegionForAddress(instruction_pointer);
  if (!region) {
    // Dunno what's going on here.
    printf("NO_JIT_MEMORY\n");
    return 0;
  }

  // Have JIT memory.
  if (context->GetContextCPU() != MD_CONTEXT_X86) {
    //TODO: deeper analysis on non-x86
    printf("NON_X86_WITH_JIT_MEMORY\n");
    return 0;
  }

  u_int32_t total = 0;
  const u_int8_t *bytes = region->GetMemory();
  u_int32_t region_size = region->GetSize();
  u_int64_t region_base = region->GetBase();
  CrashError most_interesting = CRASH_UNKNOWN;
  while (total <= region_size) {
    DisassemblerX86 dis(bytes + total, region_size - total, region_base);
    DisRegion r = AnalyzeCodeRegion(dis, region_size - total, region_base + total, instruction_pointer);

    // Have we found EIP yet?
    bool seen_ip = (region_base + total + r.bytes > instruction_pointer);

    // If nothing could be disassembled, but we've seen valid code, try to inch along.
    if (r.bytes < 6 && !seen_ip) {
      total++;
      continue;
    }

    // Try and find the most serious problem.
    if (r.error > most_interesting)
      most_interesting = r.error;
    if (seen_ip || most_interesting == CRASH_REASONS - 1)
      break;

    total += r.bytes;
  }

  printf("%s\n", CrashReasons[most_interesting]);

  return 0;
}

static CrashError
IsSensibleInstruction(libdis::x86_insn_t *insn, bool is_ip = false);

static CrashError
IsSensibleOperand(libdis::x86_insn_t *insn, libdis::x86_op_t *op)
{
  switch (op->type) {
    case libdis::op_expression:
    {
      libdis::x86_ea_t ea = op->data.expression;
      if (ea.disp >= 0x10000000)
        return CRASH_CORRUPT_CODE;
      return CRASH_UNKNOWN;
    }
    default:
      return CRASH_UNKNOWN;
  }
}

static CrashError
IsSensibleOperandPair(libdis::x86_insn_t *insn, libdis::x86_op_t *op1, libdis::x86_op_t *op2)
{
  return CRASH_UNKNOWN;
}

static CrashError
IsSensibleInstruction(libdis::x86_insn_t *insn, bool is_ip)
{
  if (!insn)
    return CRASH_CORRUPT_CODE;

  // When executing a block of zeroes we get a two-byte "00 00" instruction
  if (insn->size == 2 && !insn->bytes[0] && !insn->bytes[1])
    return CRASH_CORRUPT_CODE;

  char buffer[255];
  x86_format_insn(insn, buffer, sizeof(buffer), libdis::intel_syntax);
//  printf("%s%x: %s\n", is_ip ? "> " : "", insn->type, buffer);

  switch (insn->type) {
    case 0xE000: /* cli/sti */
    case libdis::insn_strcmp:
    case libdis::insn_strload:
    case libdis::insn_inc:
    case libdis::insn_dec:
    case libdis::insn_tog_carry:
    case libdis::insn_set_carry:
    case libdis::insn_clear_carry:
    case libdis::insn_in:
    case libdis::insn_out:
    case libdis::insn_translate:
    case libdis::insn_oflow:
    case libdis::insn_bcdconv:
    case libdis::insn_rol:
    case libdis::insn_ror:
      return CRASH_CORRUPT_CODE;

    case libdis::insn_add:
      if (strncmp(buffer, "adc", 3) == 0)
        return CRASH_CORRUPT_CODE;
      break;
    case libdis::insn_sub:
      if (strncmp(buffer, "sbb", 3) == 0)
        return CRASH_CORRUPT_CODE;
      break;
    case libdis::insn_pushregs:
      if (strncmp(buffer, "pusha", 5) == 0)
        return CRASH_CORRUPT_CODE;
      if (strncmp(buffer, "popa", 4) == 0)
        return CRASH_CORRUPT_CODE;
      break;
    case libdis::insn_return:
      if (strncmp(buffer, "retf", 4) == 0)
        return CRASH_CORRUPT_CODE;
      break;
    case libdis::insn_jcc:
      if (strncmp(buffer, "loopnz", 6) == 0)
        return CRASH_CORRUPT_CODE;
      break;
    case libdis::insn_cmp:
    case libdis::insn_mov:
    {
      libdis::x86_op_t *op1 = x86_operand_1st(insn);
      if (!op1)
        break;
      if (CrashError error = IsSensibleOperand(insn, op1))
        return error;
      libdis::x86_op_t *op2 = x86_operand_2nd(insn);
      if (!op2)
        break;
      if (CrashError error = IsSensibleOperand(insn, op2))
        return error;
      if (CrashError error = IsSensibleOperandPair(insn, op1, op2))
        return error;
      break;
    }

    default:
      break;
  }

  return CRASH_UNKNOWN;
}

static CrashError
ValidateInstructionPointer(DisassemblerX86 &dis, libdis::x86_insn_t *insn)
{
  // Check flags
  u_int16_t flags = dis.flags();
  if (flags & DISX86_BAD_BRANCH_TARGET)
    return CRASH_BAD_BRANCH_TARGET;
  return CRASH_UNKNOWN;
}

static DisRegion
AnalyzeCodeRegion(DisassemblerX86 &dis, u_int32_t limit, u_int64_t start, u_int64_t ip)
{
  bool hit_ip_insn = false;
  u_int32_t bytes_disassembled = 0;
  while (bytes_disassembled <= limit) {
    bool is_ip = start + bytes_disassembled == ip;
    u_int32_t num_bytes = dis.NextInstruction();
    if (!num_bytes)
      break;
    bytes_disassembled += num_bytes;

    libdis::x86_insn_t *insn = const_cast<libdis::x86_insn_t *>(dis.currentInstruction());

    if (is_ip) {
      hit_ip_insn = true;
      CrashError error = ValidateInstructionPointer(dis, insn);
      if (error)
        return DisRegion(error, bytes_disassembled);
    }

    if (!insn && start + bytes_disassembled > ip)
      return DisRegion(CRASH_UNKNOWN, bytes_disassembled);

    CrashError error = IsSensibleInstruction(insn, is_ip);
    if (error) {
      if (error == CRASH_CORRUPT_CODE && is_ip)
        error = CRASH_BAD_EIP_INSTRUCTION;
      return DisRegion(error, bytes_disassembled);
    }
  }

  if (bytes_disassembled == 0)
    return DisRegion(CRASH_CORRUPT_CODE, bytes_disassembled);

  if (!hit_ip_insn && (ip >= start && ip <= start + bytes_disassembled))
    return DisRegion(CRASH_EIP_IN_BETWEEN, bytes_disassembled);

  return DisRegion(CRASH_UNKNOWN, bytes_disassembled);
}
