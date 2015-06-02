// Copyright (c) 2015 The Mozilla Foundation
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

#ifndef STACKWALKER_COMMON_H_
#define STACKWALKER_COMMON_H_

#include <vector>

#include <stdio.h>
#include <sys/stat.h>

// For inserting into a static struct option[]
const struct option kHTTPCommandLineOptions[] = {
    {"symbols-url", required_argument, nullptr, 's'},
    {"symbols-cache", required_argument, nullptr, 'c'},
    {"symbols-tmp", required_argument, nullptr, 't'}
};

#define HTTP_COMMANDLINE_OPTIONS \
  kHTTPCommandLineOptions[0], \
  kHTTPCommandLineOptions[1], \
  kHTTPCommandLineOptions[2],

// For inserting into usage()
void http_commandline_usage() {
  fprintf(stderr, "\t--symbols-url\tA base URL from which URLs to symbol files can be constructed\n");
  fprintf(stderr, "\t--symbols-cache\tA directory in which downloaded symbols can be stored\n");
  fprintf(stderr, "\t--symbols-tmp\tA directory to use as temp space for downloading symbols. Must be on the same filesystem as symbols-cache.\n");
}

// For inserting into the switch handling for getopt_long
#define HANDLE_HTTP_COMMANDLINE_OPTIONS \
    case 's': \
      symbols_urls.push_back(optarg); \
      break; \
    case 'c': \
      symbols_cache = optarg; \
      break; \
    case 't': \
      symbols_tmp = optarg; \
      break;

bool same_filesystem(const char* a, const char* b) {
  struct stat sta, stb;
  return stat(a, &sta) == 0 && stat(b, &stb) == 0
    && sta.st_dev == stb.st_dev;
}

bool check_http_commandline_options(
    const std::vector<char*>& symbols_urls,
    const char* symbols_cache,
    const char* symbols_tmp) {
  if ((!symbols_urls.empty() || symbols_cache) &&
      !(!symbols_urls.empty() && symbols_cache)) {
    fprintf(stderr, "You must specify both --symbols-url and --symbols-cache "
            "when using one of these options\n");
    return false;
  }

  if (symbols_cache && !same_filesystem(symbols_cache, symbols_tmp)) {
    fprintf(stderr, "Error: --symbols-cache and --symbols-tmp "
            "paths must be on the same filesystem\n");
    return false;
  }
  return true;
}

#endif  // STACKWALKER_COMMON_H_
