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

#include "http_symbol_supplier.h"

#include <algorithm>

#include <curl/curl.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>

#include <errno.h>

#include "google_breakpad/processor/code_module.h"
#include "google_breakpad/processor/system_info.h"
#include "processor/logging.h"
#include "processor/pathname_stripper.h"

namespace breakpad_extra {

using google_breakpad::CodeModule;
using google_breakpad::PathnameStripper;
using google_breakpad::SystemInfo;

static bool file_exists(const string& file_name) {
  struct stat sb;
  return stat(file_name.c_str(), &sb) == 0;
}

static string dirname(const string& path) {
  size_t i = path.rfind('/');
  if (i == string::npos) {
    return path;
  }
  return path.substr(0, i);
}

static bool mkdirs(const string& file) {
  vector<string> dirs;
  string dir = dirname(file);
  while (!file_exists(dir)) {
    dirs.push_back(dir);
    string new_dir = dirname(dir);
    if (new_dir == dir || dir.empty()) {
      break;
    }
    dir = new_dir;
  }
  for (auto d = dirs.rbegin(); d != dirs.rend(); ++d) {
    if (mkdir(d->c_str(), 0755) != 0) {
      BPLOG(ERROR) << "Error creating " << *d << ": " << errno;
      return false;
    }
  }
  return true;
}

static vector<string> vector_from(const string& front,
                                  const vector<string>& rest) {
  vector<string> vec(1, front);
  std::copy(rest.begin(), rest.end(), std::back_inserter(vec));
  return vec;
}

HTTPSymbolSupplier::HTTPSymbolSupplier(const vector<string>& server_urls,
                                       const string& cache_path,
				       const vector<string>& local_paths,
                                       const string& tmp_path)
  : SimpleSymbolSupplier(vector_from(cache_path, local_paths)),
    server_urls_(server_urls),
    cache_path_(cache_path),
    tmp_path_(tmp_path),
    curl_(curl_easy_init()) {
  for (auto i = server_urls_.begin(); i < server_urls_.end(); ++i) {
    if (*(i->end() - 1) != '/') {
      i->push_back('/');
    }
  }
  // Remove any trailing slash on tmp_path.
  if (!tmp_path_.empty() && tmp_path_.back() == '/') {
    tmp_path_.erase(tmp_path_.end() - 1);
  }
}

HTTPSymbolSupplier::~HTTPSymbolSupplier() {
  curl_easy_cleanup(curl_);
}

void
HTTPSymbolSupplier::StoreSymbolStats(const CodeModule* module,
                                     const SymbolStats& stats) {
  const auto& key =
    std::make_pair(module->debug_file(), module->debug_identifier());
  if (symbol_stats_.find(key) == symbol_stats_.end()) {
    symbol_stats_[key] = stats;
  }
}

string
HTTPSymbolSupplier::GuessURL(const CodeModule* module)
{
  string path, url;
  if (!server_urls_.empty()
      && GetRelativeURLAndPathToSymbolFile(module, url, path)) {
    return server_urls_.front() + url;
  }
  return "";
}

void
HTTPSymbolSupplier::StoreCacheHit(const CodeModule* module)
{
  // We don't know the original URL, so guess that it would have
  // been from the first URL we would have tried.
  SymbolStats stats = {true, 0.0f, GuessURL(module)};
  StoreSymbolStats(module, stats);
}

void
HTTPSymbolSupplier::StoreCacheMiss(const CodeModule* module,
                                   float fetch_time,
                                   const string& url)
{
  SymbolStats stats = {false, fetch_time, url};
  StoreSymbolStats(module, stats);
}

SymbolSupplier::SymbolResult
HTTPSymbolSupplier::GetSymbolFile(const CodeModule* module,
                                  const SystemInfo* system_info,
                                  string* symbol_file) {
  SymbolSupplier::SymbolResult res =
    SimpleSymbolSupplier::GetSymbolFile(module, system_info, symbol_file);
  if (res != SymbolSupplier::NOT_FOUND) {
    StoreCacheHit(module);
    return res;
  }

  if (!FetchSymbolFile(module, system_info)) {
    return SymbolSupplier::NOT_FOUND;
  }

  return SimpleSymbolSupplier::GetSymbolFile(module, system_info, symbol_file);
}

SymbolSupplier::SymbolResult
HTTPSymbolSupplier::GetSymbolFile(const CodeModule* module,
                                  const SystemInfo* system_info,
                                  string* symbol_file,
                                  string* symbol_data) {
  SymbolSupplier::SymbolResult res =
    SimpleSymbolSupplier::GetSymbolFile(module, system_info,
                                        symbol_file, symbol_data);
  if (res != SymbolSupplier::NOT_FOUND) {
    StoreCacheHit(module);
    return res;
  }

  if (!FetchSymbolFile(module, system_info)) {
    return SymbolSupplier::NOT_FOUND;
  }

  return SimpleSymbolSupplier::GetSymbolFile(module, system_info,
                                             symbol_file, symbol_data);
}

SymbolSupplier::SymbolResult
HTTPSymbolSupplier::GetCStringSymbolData(const CodeModule *module,
                                         const SystemInfo *system_info,
                                         string *symbol_file,
                                         char **symbol_data,
                                         size_t* size) {
  SymbolSupplier::SymbolResult res =
    SimpleSymbolSupplier::GetCStringSymbolData(module, system_info,
                                               symbol_file, symbol_data,
                                               size);
  if (res != SymbolSupplier::NOT_FOUND) {
    StoreCacheHit(module);
    return res;
  }

  if (!FetchSymbolFile(module, system_info)) {
    return SymbolSupplier::NOT_FOUND;
  }

  return SimpleSymbolSupplier::GetCStringSymbolData(module, system_info,
                                                    symbol_file, symbol_data,
                                                    size);
}

namespace {
  string URLEncode(CURL* curl, const string& url) {
    char* escaped_url_raw = curl_easy_escape(curl,
                                             const_cast<char*>(url.c_str()),
					     url.length());
    if (not escaped_url_raw) {
      BPLOG(INFO) << "HTTPSymbolSupplier: couldn't escape URL: " << url;
      return "";
    }
    string escaped_url(escaped_url_raw);
    curl_free(escaped_url_raw);
    return escaped_url;
  }

  string JoinPath(const string& path, const string& sub) {
    return path + "/" + sub;
  }

  string JoinURL(CURL* curl, const string& url, const string& sub) {
    return url + "/" + URLEncode(curl, sub);
  }

  string GetCodeIDAndFileQueryString(CURL* curl, const CodeModule* module) {
      string code_file = PathnameStripper::File(module->code_file());
      if (code_file.empty()) {
        return "";
      }

      string code_id = PathnameStripper::File(module->code_identifier());
      if (code_id.empty()) {
        return "";
      }

      return "?code_file=" + URLEncode(curl, code_file) + "&code_id=" + URLEncode(curl, code_id);
  }
}

bool
HTTPSymbolSupplier::GetRelativeURLAndPathToSymbolFile(const CodeModule* module,
                                                      string& out_url,
                                                      string& out_path)
{
  // Copied from simple_symbol_supplier.cc
  string debug_file_name = PathnameStripper::File(module->debug_file());
  if (debug_file_name.empty()) {
    return false;
  }
  string path = debug_file_name;
  string url = URLEncode(curl_, debug_file_name);

  // Append the identifier as a directory name.
  string identifier = module->debug_identifier();
  if (identifier.empty()) {
    return false;
  }
  path = JoinPath(path, identifier);
  url = JoinURL(curl_, url, identifier);

  // Transform the debug file name into one ending in .sym.  If the existing
  // name ends in .pdb, strip the .pdb.  Otherwise, add .sym to the non-.pdb
  // name.
  string debug_file_extension;
  if (debug_file_name.size() > 4) {
    debug_file_extension = debug_file_name.substr(debug_file_name.size() - 4);
  }
  std::transform(debug_file_extension.begin(), debug_file_extension.end(),
                 debug_file_extension.begin(), tolower);
  if (debug_file_extension == ".pdb") {
    debug_file_name = debug_file_name.substr(0, debug_file_name.size() - 4);
  }

  debug_file_name += ".sym";
  out_path = JoinPath(path, debug_file_name);
  out_url = JoinURL(curl_, url, debug_file_name);
  return true;
}

bool HTTPSymbolSupplier::FetchSymbolFile(const CodeModule* module,
                                         const SystemInfo* system_info) {
  // See if we already attempted to fetch this symbol file.
  if (SymbolWasError(module, system_info)) {
    return false;
  }

  string path, url;
  if (!GetRelativeURLAndPathToSymbolFile(module, url, path)) {
    return false;
  }

  string query = GetCodeIDAndFileQueryString(curl_, module);

  string full_path = JoinPath(cache_path_, path);

  bool result = false;
  for (auto server_url = server_urls_.begin();
       server_url < server_urls_.end();
       ++server_url) {
    string full_url = *server_url + url;
    string url_with_query = full_url;
    if (!query.empty()) {
      url_with_query += query;
    }
    float fetch_time;
    if (FetchURLToFile(curl_, url_with_query, full_path, &fetch_time)) {
      StoreCacheMiss(module, fetch_time, full_url);
      result = true;
      break;
    }
  }
  if (!result) {
    error_symbols_.insert(std::make_pair(module->debug_file(),
                                         module->debug_identifier()));
  }
  return result;
}

bool HTTPSymbolSupplier::FetchURLToFile(CURL* curl,
                                        const string& url,
                                        const string& file,
                                        float* fetch_time) {
  BPLOG(INFO) << "HTTPSymbolSupplier: fetching " << url;
  *fetch_time = 0.0f;

  string tempfile = JoinPath(tmp_path_, "symbolXXXXXX");
  int fd = mkstemp(&tempfile[0]);
  if (fd == -1) {
    return false;
  }
  FILE* f = fdopen(fd, "w");

  BPLOG(INFO) << "HTTPSymbolSupplier: querying " << url;

  curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
  curl_easy_setopt(curl, CURLOPT_ENCODING, "");
  curl_easy_setopt(curl, CURLOPT_STDERR, stderr);
  curl_easy_setopt(curl, CURLOPT_WRITEDATA, f);
  curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1);

  struct timeval t1, t2;
  gettimeofday(&t1, nullptr);
  bool result = false;
  long retcode = -1;
  if (curl_easy_perform(curl) != 0) {
    BPLOG(INFO) << "HTTPSymbolSupplier: curl_easy_perform failed";
  }
  else if (curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &retcode) != 0) {
    BPLOG(INFO) << "HTTPSymbolSupplier: curl_easy_getinfo failed";
  }
  else if (retcode != 200) {
    BPLOG(INFO) << "HTTPSymbolSupplier: HTTP response code: " << retcode;
  }
  else {
    BPLOG(INFO) << "HTTPSymbolSupplier: fetch succeeded, saving to " << file;
    result = true;
  }
  gettimeofday(&t2, nullptr);
  *fetch_time = (t2.tv_sec - t1.tv_sec) * 1000.0
    + (t2.tv_usec - t1.tv_usec) / 1000.0;
  fclose(f);
  close(fd);

  if (result) {
    result = mkdirs(file);
    if (!result) {
      BPLOG(INFO) << "HTTPSymbolSupplier: failed to create directories for "
                  << file;
    }
  }
  if (result) {
    result = 0 == rename(tempfile.c_str(), file.c_str());
    if (!result) {
      int e = errno;
      BPLOG(INFO) << "HTTPSymbolSupplier: failed to rename file, errno=" << e;
    }
  }

  if (!result) {
    unlink(tempfile.c_str());
  }

  return result;
}

bool
HTTPSymbolSupplier::GetStats(const CodeModule* module, SymbolStats* stats) const {
  const auto& found =
    symbol_stats_.find(std::make_pair(module->debug_file(),
                                      module->debug_identifier()));
  if (found == symbol_stats_.end()) {
    return false;
  }

  *stats = found->second;
  return true;
}

bool HTTPSymbolSupplier::SymbolWasError(const CodeModule* module,
                                        const SystemInfo* system_info) {
  return error_symbols_.find(std::make_pair(module->debug_file(),
                                            module->debug_identifier())) !=
    error_symbols_.end();
}

}
