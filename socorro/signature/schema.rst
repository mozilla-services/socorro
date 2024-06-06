Signature generation crash data schema
======================================

This is the schema for the signature generation crash data structure::

  {
    platform: <string>,                // Optional, the platform for the crash. Currently one of
                                       // "c" or "java". Defaults to "c".
                                       //
                                       // These match Sentry platform values.

    crashing_thread: <int or null>,    // Optional, The index of the crashing thread in threads.
                                       // This defaults to None which indicates there was no
                                       // crashing thread identified in the crash report.
                                       //
                                       // Platform: c

    reason: <string>,                  // Optional, The crash_info type value. This can indicate
                                       // the crash was a OOM.
                                       //
                                       // Platform: c

    os: <string>,                      // Optional, The name of the operating system. This
                                       // doesn't affect anything unless the name is "Windows
                                       // NT" in which case it will lowercase module names when
                                       // iterating through frames to build the signature.
                                       //
                                       // Platform: c

    threads: <threads_structure>,      // Optional, list of stack traces for c/c++/rust code.
                                       //
                                       // Platform: c

    java_stack_trace: <string>,        // Optional, If the crash is a Java crash, then this will
                                       // be the Java traceback as a single string. Signature
                                       // generation will split this string into lines and then
                                       // extract frame information from it to generate the
                                       // signature.
                                       //
                                       // Platform: java

                                       // FIXME(willkg): Write up better description of this.

    java_exception: <java_exception_structure>,
                                       // Optional, the exception structure.
                                       //
                                       // For Java crashes with a JavaException annotation, this
                                       // will be the value.

    oom_allocation_size: <int>,        // Optional, The allocation size that triggered an
                                       // out-of-memory error. This will get added to the
                                       // signature if one of the indicator functions appears in
                                       // the stack of the crashing thread.

    abort_message: <string>,           // Optional, The abort message for the crash, if there is
                                       // one. This is added to the beginning of the signature.

    hang_type: <int>,                  // Optional.
                                       // 1 here indicates this is a chrome hang and we look at
                                       // thread 0 for generation.
                                       // -1 indicates another kind of hang.

    async_shutdown_timeout: <text>,    // Optional, This is a text field encoded in JSON with
                                       // "phase" and "conditions" keys.
                                       // FIXME(willkg): Document this structure better.

    jit_category: <string>,            // Optional, If there's a JIT classification in the
                                       // crash, then that will override the signature

    ipc_channel_error: <string>,       // Optional, If there is an IPC channel error, it
                                       // replaces the signature.

    ipc_message_name: <string>,        // Optional, This gets added to the signature if there
                                       // was an IPC message name in the crash.

    additional_minidumps: <string>,    // Optional, A crash report can contain multiple minidumps.
                                       // This is a comma-delimited list of minidumps other than
                                       // the main one that the crash had.

                                       // Example: "browser,flash1,flash2,content"

    mdsw_status_string: <string>,      // Optional, Socorro-generated
                                       // This is the minidump-stackwalk status string. This
                                       // gets generated when the Socorro processor runs the
                                       // minidump through minidump-stackwalk. If you're not
                                       // using minidump-stackwalk, you can ignore this.
  }


Thread structure (c platform only)::

  [
    {
      frames: [                        // List of one or more frames.
        {
          function: <string>,          // Optional, the name of the function.
                                       // If this is ``None`` or not in the frame, then signature
                                       // generation will calculate something using other data in
                                       // the frame.

          module: <string>,            // Optional, name of the module
          file: <string>,              // Optional, name of the file
          line: <int>,                 // Optional, line in the file
          module_offset: <string>,     // Optional, offset in hex in the module for this frame
          offset: <string>             // Optional, offset in hex for this frame

                                       // Signature parts are computed using frame data in this
                                       // order:

                                       // 1. if there's a function (and optionally line)--use
                                       //    that
                                       // 2. if there's a file and a line--use that
                                       // 3. if there's an offset and no module/module_offset--use
                                       //    that
                                       // 4. use module/module_offset
        }
        // ... additional frames
      ],

      thread_name: <string>,           // Optional, The name of the thread.
                                       // This isn't used, yet, but might be in the future for
                                       // debugging purposes.

      frame_count: <int>               // Optional, This is the total number of frames. This
                                       // isn't used.
    }
    // ... additional threads
  ],


Java exception structure::

  {
    exception: {                       // Exception

      values: [                        // Exception value--there will be multiple values in a
                                       // cascading exception in order of oldest to newest where
                                       // the start of the cascade if first.

        stacktrace: {                  // A stacktrace.

          frames: [                    // A list of frames in the stack trace sorted newest
                                       // to oldest so that the first frame is then one that
                                       // had the exception.
            {
              module: <string>,        // Optional, name of the module

              function: <string>,      // Optional, the name of the function

              in_app: <boolean>,       // Optional, whether this frame is relevant to the
                                       // execution of the relevant code in the app.

              lineno: <int>,           // Optional, line in the file

              filename: <string>,      // Optional, name of the file
            },
            // ... additional frames
          ],

          type: <string>,              // Optional, exception type

          module: <string>,            // Optional, module the exception lives in

          value: <string>              // Optional, exception value
        },
        // ... additional stacktraces
      ]
    }
  }


Missing keys in the structure are treated as ``None``, so you can pass in a
minimal structure with just the parts you define.
