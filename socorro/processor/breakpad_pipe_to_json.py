# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module provides a function that will transate Minidump Stackwalk pipe
dump into a json format.

{
  # "status": string, // OK | ERROR_* | SYMBOL_SUPPLIER_INTERRUPTED
  "system_info": {
    "os": string,
    "os_ver": string,
    "cpu_arch": string, // x86 | amd64 | arm | ppc | sparc
    "cpu_info": string,
    "cpu_count": int
  },
  "crash_info": {
    "type": string,
    "crash_address": string, // 0x[[:xdigit:]]+
    "crashing_thread": int // | null
  }
  "main_module": int, // index into modules
  "modules": [
         // zero or more
    {
      "base_addr": string, // 0x[[:xdigit:]]+
      "debug_file": string,
      "debug_id": string, // [[:xdigit:]]{33}
      "end_addr": string, // 0x[[:xdigit:]]+
      "filename": string,
      "version": string
    }
  ],
  "thread_count": int,
  "threads": [
    // for i in range(thread_count)
    {
      "frame_count": int,
      "frames": [
        // for i in range(frame_count)
        {
          "frame": int,
          "module": string,   // optional
          "function": string, // optional
          "file": string,     // optional
          "line": int,        // optional
          "offset": string,         // 0x[[:xdigit:]]+
          "module_offset": string,  // 0x[[:xdigit:]]+ , optional
          "function_offset": string // 0x[[:xdigit:]]+ , optional
        }
      ]
    }
  ],
  // repeated here for ease of searching
  // (max 10 frames)
  "crashing_thread": {
    "threads_index": int,
    "total_frames": int,
    "frames": [
      // for i in range(length)
      {
        // as per "frames" entries from "threads" above
      }
    ]
  }
}
"""

from socorro.lib.util import DotDict


#==============================================================================
class DotDictWithPut(DotDict):
    #--------------------------------------------------------------------------
    def put_if_not_none(self, key, value):
        if value is not None and value != '':
            self[key] = value


#------------------------------------------------------------------------------
def pipe_dump_to_json_dump(pipe_dump_iterable):
    """given a list (or any iterable) of strings representing a MDSW pipe dump,
    this function will convert it into a json format."""
    json_dump = DotDict()
    crashing_thread = None
    module_counter = 0
    thread_counter = 0
    for a_line in pipe_dump_iterable:
        parts = a_line.split('|')
        if parts[0] == 'OS':
            _extract_OS_info(parts, json_dump)
        elif parts[0] == 'CPU':
            _extract_CPU_info(parts, json_dump)
        elif parts[0] == 'Crash':
            crashing_thread = _extract_crash_info(parts, json_dump)
        elif parts[0] == 'Module':
            _extract_module_info(parts, json_dump, module_counter)
            module_counter += 1
        else:
            try:
                thread_number = int(parts[0])
            except (ValueError, IndexError):
                continue  # unknow line type, ignore it
            _extract_frame_info(parts, json_dump)
    try:
        json_dump.thread_count = len(json_dump.threads)
    except KeyError:  # no threads were over found, 'threads' key was not made
        json_dump.thread_count = 0
    if crashing_thread is not None:
        crashing_thread_frames = DotDict()
        crashing_thread_frames.threads_index = crashing_thread
        crashing_thread_frames.total_frames = \
            len(json_dump.threads[crashing_thread].frames)
        crashing_thread_frames.frames = \
            json_dump.threads[crashing_thread].frames[:10]
        json_dump.crashing_thread = crashing_thread_frames
    return json_dump


#------------------------------------------------------------------------------
def _get(indexable_container, index, default):
    """like 'get' on a dict, but it works on lists, too"""
    try:
        return indexable_container[index]
    except (IndexError, KeyError):
        return default

#------------------------------------------------------------------------------
def _get_int(indexable_container, index, default):
    """try to get an int from an indexable container.  If that fails
    return the default"""
    try:
        return int(indexable_container[index])
    # exceptions separated to make case coverage clearer
    except (IndexError, KeyError):
        # item not found in the container
        return default
    except ValueError:
        # conversion to integer has failed
        return default

#------------------------------------------------------------------------------
def _extract_OS_info(os_line, json_dump):
    """given a pipe dump OS line, extract the parts and put them in their
    proper location within the json_dump"""
    system_info = DotDictWithPut()
    system_info.put_if_not_none('os', _get(os_line, 1, None))
    system_info.put_if_not_none('os_ver', _get(os_line, 2, None))
    if 'system_info' in json_dump:
        json_dump.system_info.update(system_info)
    else:
        json_dump.system_info = system_info

#------------------------------------------------------------------------------
def _extract_CPU_info(cpu_line, json_dump):
    """given a pipe dump CPU line, extract the parts and put them in their
    proper location within the json_dump"""
    system_info = DotDictWithPut()
    system_info.put_if_not_none('cpu_arch', _get(cpu_line, 1, None))
    system_info.put_if_not_none('cpu_info', _get(cpu_line, 2, None))
    system_info.put_if_not_none('cpu_count', _get_int(cpu_line, 3, None))
    if 'system_info' in json_dump:
        json_dump.system_info.update(system_info)
    else:
        json_dump.system_info = system_info

#------------------------------------------------------------------------------
def _extract_crash_info(crash_line, json_dump):
    """given a pipe dump CRASH line, extract the parts and put them in their
    proper location within the json_dump"""
    crash_info = DotDictWithPut()
    crash_info.put_if_not_none('type', _get(crash_line, 1, None))
    crash_info.put_if_not_none('crash_address', _get(crash_line, 2, None))
    crash_info.put_if_not_none('crashing_thread', _get_int(crash_line, 3, None))
    json_dump.crash_info = crash_info
    return crash_info.get('crashing_thread', None)


#------------------------------------------------------------------------------
def _extract_module_info(module_line, json_dump, module_counter):
    """given a pipe dump Module line, extract the parts and put them in their
    proper location within the json_dump"""
    module = DotDictWithPut()
    module.put_if_not_none('filename', _get(module_line, 1, None))
    module.put_if_not_none('version', _get(module_line, 2, None))
    module.put_if_not_none('debug_file', _get(module_line, 3, None))
    module.put_if_not_none('debug_id', _get(module_line, 4, None))
    module.put_if_not_none('base_addr', _get(module_line, 5, None))
    module.put_if_not_none('end_addr', _get(module_line, 6, None))
    is_main_module = _get_int(module_line, 7, 0)
    if is_main_module:
        json_dump.main_module = module_counter
    if 'modules' not in json_dump:
        json_dump.modules = []
    json_dump.modules.append(module)

#------------------------------------------------------------------------------
def _extract_frame_info(frame_line, json_dump):
    """given a pipe dump Frame line, extract the parts and put them in their
    proper location within the json_dump"""
    if 'threads' not in json_dump:
        json_dump.threads = []
    thread_number = _get_int(frame_line, 0, None)
    if thread_number is None:
        return
    if thread_number >=len(json_dump.threads):
        # threads are supposed to arrive in order.  We've not seen this thread
        # before, fill in a new entry in the 'threads' section of the json_dump
        # making sure that intervening missing threads have empty thread data
        for i in range(thread_number - len(json_dump.threads) + 1):
            thread = DotDict()
            thread.frame_count = 0
            thread.frames = []
            json_dump.threads.append(thread)
    # collect frame info from the pipe dump line
    tmp_frame = _get_int(frame_line, 1, None)
    tmp_module = _get(frame_line, 2, None)
    tmp_function = _get(frame_line, 3, None)
    tmp_file = _get(frame_line, 4, None)
    tmp_line = _get_int(frame_line, 5, None)
    tmp_offset = _get(frame_line, 6, None)
    frame = DotDictWithPut()
    frame.put_if_not_none('frame', tmp_frame)
    frame.put_if_not_none('module', tmp_module)
    frame.put_if_not_none('function', tmp_function)
    frame.put_if_not_none('file', tmp_file)
    frame.put_if_not_none('line', tmp_line)
    if tmp_file and tmp_line is not None:
        # skip offset entirely
        pass
    elif not tmp_file and tmp_function:
        frame.function_offset = tmp_offset
    elif not tmp_function and tmp_module:
        frame.module_offset = tmp_offset
    else:
        frame.offset = tmp_offset
    # save the frame info into the json
    json_dump.threads[thread_number].frames.append(frame)
    json_dump.threads[thread_number].frame_count += 1

