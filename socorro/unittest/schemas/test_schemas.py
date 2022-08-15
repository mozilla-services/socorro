# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import jsonschema
import pytest

from socorro.lib.libjson import traverse_schema
from socorro.schemas import get_file_content, PROCESSED_CRASH_SCHEMA


def test_validate_schemas(reporoot):
    """Validate the schemas are themselves valid jsonschema"""
    path = reporoot / "socorro" / "schemas"

    # Validate JSON-specified schemas are valid jsonschema
    for fn in path.glob("*.json"):
        print(fn)
        schema = get_file_content(fn.name)
        jsonschema.Draft4Validator.check_schema(schema)

    # Validate YAML-specified schemas are valid jsonschema
    for fn in path.glob("*.yaml"):
        print(fn)
        schema = get_file_content(fn.name)
        jsonschema.Draft4Validator.check_schema(schema)


class PermissionsMissingError(Exception):
    pass


def split_path(path):
    """Split a general path into parts

    This handles the case where patternProperties parts are enclosed in parens and can
    contain . which is a regex thing.

    :arg path: a path to split

    :returns: generator of parts

    """
    part = []
    in_paren = False
    for c in path:
        if in_paren:
            if c == ")":
                in_paren = False
            part.append(c)
        elif c == "(":
            in_paren = True
            part.append(c)
        elif c == ".":
            if part:
                yield "".join(part)
            part = []
        else:
            part.append(c)

    if part:
        yield "".join(part)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", []),
        (".java_exception", ["java_exception"]),
        (
            ".java_exception.exception.values.[].stacktrace.frames.[].filename",
            [
                "java_exception",
                "exception",
                "values",
                "[]",
                "stacktrace",
                "frames",
                "[]",
                "filename",
            ],
        ),
        (
            ".json_dump.crashing_thread.frames.[].registers.(re:^.+$)",
            ["json_dump", "crashing_thread", "frames", "[]", "registers", "(re:^.+$)"],
        ),
    ],
)
def test_split_parts(path, expected):
    assert list(split_path(path)) == expected


class NonPublicParentError(Exception):
    pass


KNOWN_PUBLIC_FIELDS = {
    "abort_message",
    "accessibility",
    "accessibility_client",
    "accessibility_in_proc_client",
    "adapter_device_id",
    "adapter_driver_version",
    "adapter_subsys_id",
    "adapter_vendor_id",
    "additional_minidumps",
    "addons",
    "addons_checked",
    "address",
    "android_board",
    "android_brand",
    "android_cpu_abi",
    "android_cpu_abi2",
    "android_device",
    "android_display",
    "android_fingerprint",
    "android_hardware",
    "android_manufacturer",
    "android_model",
    "android_version",
    "app_init_dlls",
    "app_notes",
    "application_build_id",
    "async_shutdown_timeout",
    "available_page_file",
    "available_physical_memory",
    "available_virtual_memory",
    "bios_manufacturer",
    "build",
    "client_crash_date",
    "co_marshal_interface_failure",
    "co_unmarshal_interface_result",
    "completed_datetime",
    "content_sandbox_capabilities",
    "content_sandbox_capable",
    "content_sandbox_enabled",
    "content_sandbox_level",
    "cpu_arch",
    "cpu_info",
    "cpu_microcode_version",
    "crash_id",
    "crash_report_keys",
    "crash_time",
    "crashing_thread",
    "date_processed",
    "distribution_id",
    "dom_fission_enabled",
    "dom_ipc_enabled",
    "em_check_compatibility",
    "flash_version",
    "gmp_plugin",
    "graphics_critical_error",
    "graphics_startup_test",
    "has_device_touch_screen",
    "install_age",
    "install_time",
    "ipc_channel_error",
    "ipc_fatal_error_msg",
    "ipc_fatal_error_protocol",
    "ipc_message_name",
    "ipc_message_size",
    "ipc_shutdown_state",
    "ipc_system_error",
    "is_garbage_collecting",
    "java_exception",
    "java_exception.exception",
    "java_exception.exception.values",
    "java_exception.exception.values.[]",
    "java_exception.exception.values.[].stacktrace",
    "java_exception.exception.values.[].stacktrace.frames",
    "java_exception.exception.values.[].stacktrace.frames.[]",
    "java_exception.exception.values.[].stacktrace.frames.[].filename",
    "java_exception.exception.values.[].stacktrace.frames.[].function",
    "java_exception.exception.values.[].stacktrace.frames.[].in_app",
    "java_exception.exception.values.[].stacktrace.frames.[].lineno",
    "java_exception.exception.values.[].stacktrace.frames.[].module",
    "java_exception.exception.values.[].stacktrace.module",
    "java_exception.exception.values.[].stacktrace.type",
    "java_exception_raw",
    "java_exception_raw.exception",
    "java_exception_raw.exception.values",
    "java_exception_raw.exception.values.[]",
    "java_exception_raw.exception.values.[].stacktrace",
    "java_exception_raw.exception.values.[].stacktrace.frames",
    "java_exception_raw.exception.values.[].stacktrace.frames.[]",
    "java_exception_raw.exception.values.[].stacktrace.frames.[].filename",
    "java_exception_raw.exception.values.[].stacktrace.frames.[].function",
    "java_exception_raw.exception.values.[].stacktrace.frames.[].in_app",
    "java_exception_raw.exception.values.[].stacktrace.frames.[].lineno",
    "java_exception_raw.exception.values.[].stacktrace.frames.[].module",
    "java_exception_raw.exception.values.[].stacktrace.module",
    "java_exception_raw.exception.values.[].stacktrace.type",
    "java_stack_trace",
    "json_dump",
    "json_dump.crash_info",
    "json_dump.crash_info.address",
    "json_dump.crash_info.assertion",
    "json_dump.crash_info.crashing_thread",
    "json_dump.crash_info.type",
    "json_dump.crashing_thread",
    "json_dump.crashing_thread.frame_count",
    "json_dump.crashing_thread.frames",
    "json_dump.crashing_thread.frames.[]",
    "json_dump.crashing_thread.frames.[].file",
    "json_dump.crashing_thread.frames.[].frame",
    "json_dump.crashing_thread.frames.[].function",
    "json_dump.crashing_thread.frames.[].function_offset",
    "json_dump.crashing_thread.frames.[].line",
    "json_dump.crashing_thread.frames.[].missing_symbols",
    "json_dump.crashing_thread.frames.[].module",
    "json_dump.crashing_thread.frames.[].module_offset",
    "json_dump.crashing_thread.frames.[].offset",
    "json_dump.crashing_thread.frames.[].registers",
    "json_dump.crashing_thread.frames.[].registers.(re:^.+$)",
    "json_dump.crashing_thread.frames.[].trust",
    "json_dump.crashing_thread.last_error_value",
    "json_dump.crashing_thread.thread_name",
    "json_dump.crashing_thread.threads_index",
    "json_dump.lsb_release",
    "json_dump.lsb_release.codename",
    "json_dump.lsb_release.description",
    "json_dump.lsb_release.id",
    "json_dump.lsb_release.release",
    "json_dump.mac_crash_info",
    "json_dump.mac_crash_info.num_records",
    "json_dump.mac_crash_info.records",
    "json_dump.mac_crash_info.records.[]",
    "json_dump.mac_crash_info.records.[].abort_cause",
    "json_dump.mac_crash_info.records.[].backtrace",
    "json_dump.mac_crash_info.records.[].dialog_mode",
    "json_dump.mac_crash_info.records.[].message",
    "json_dump.mac_crash_info.records.[].message2",
    "json_dump.mac_crash_info.records.[].module",
    "json_dump.mac_crash_info.records.[].signature_string",
    "json_dump.mac_crash_info.records.[].thread",
    "json_dump.modules",
    "json_dump.modules.[]",
    "json_dump.modules.[].base_addr",
    "json_dump.modules.[].cert_subject",
    "json_dump.modules.[].code_id",
    "json_dump.modules.[].corrupt_symbols",
    "json_dump.modules.[].debug_file",
    "json_dump.modules.[].debug_id",
    "json_dump.modules.[].end_addr",
    "json_dump.modules.[].filename",
    "json_dump.modules.[].loaded_symbols",
    "json_dump.modules.[].missing_symbols",
    "json_dump.modules.[].symbol_url",
    "json_dump.modules.[].version",
    "json_dump.modules_contains_cert_info",
    "json_dump.pid",
    "json_dump.status",
    "json_dump.system_info",
    "json_dump.system_info.cpu_arch",
    "json_dump.system_info.cpu_count",
    "json_dump.system_info.cpu_info",
    "json_dump.system_info.cpu_microcode_version",
    "json_dump.system_info.os",
    "json_dump.system_info.os_ver",
    "json_dump.thread_count",
    "json_dump.threads",
    "json_dump.threads.[]",
    "json_dump.threads.[].frame_count",
    "json_dump.threads.[].frames",
    "json_dump.threads.[].frames.[]",
    "json_dump.threads.[].frames.[].file",
    "json_dump.threads.[].frames.[].frame",
    "json_dump.threads.[].frames.[].function",
    "json_dump.threads.[].frames.[].function_offset",
    "json_dump.threads.[].frames.[].line",
    "json_dump.threads.[].frames.[].missing_symbols",
    "json_dump.threads.[].frames.[].module",
    "json_dump.threads.[].frames.[].module_offset",
    "json_dump.threads.[].frames.[].offset",
    "json_dump.threads.[].frames.[].registers",
    "json_dump.threads.[].frames.[].registers.(re:^.+$)",
    "json_dump.threads.[].frames.[].trust",
    "json_dump.threads.[].last_error_value",
    "json_dump.threads.[].thread_name",
    "last_crash",
    "mac_available_memory_sysctl",
    "mac_crash_info",
    "mac_memory_pressure",
    "mac_memory_pressure_critical_time",
    "mac_memory_pressure_normal_time",
    "mac_memory_pressure_sysctl",
    "mac_memory_pressure_warning_time",
    "major_version",
    "mdsw_return_code",
    "mdsw_status_string",
    "memory_error_correction",
    "memory_measures",
    "memory_measures.explicit",
    "memory_measures.gfx_textures",
    "memory_measures.ghost_windows",
    "memory_measures.heap_allocated",
    "memory_measures.heap_overhead",
    "memory_measures.heap_unclassified",
    "memory_measures.host_object_urls",
    "memory_measures.images",
    "memory_measures.js_main_runtime",
    "memory_measures.private",
    "memory_measures.resident",
    "memory_measures.resident_unique",
    "memory_measures.system_heap_allocated",
    "memory_measures.top_none_detached",
    "memory_measures.vsize",
    "memory_measures.vsize_max_contiguous",
    "minidump_sha256_hash",
    "modules_in_stack",
    "moz_crash_reason",
    "oom_allocation_size",
    "os_name",
    "os_pretty_version",
    "os_version",
    "plugin_filename",
    "plugin_name",
    "plugin_version",
    "process_type",
    "processor_notes",
    "product",
    "productid",
    "proto_signature",
    "reason",
    "release_channel",
    "remote_type",
    "safe_mode",
    "shutdown_progress",
    "signature",
    "signature_debug",
    "stackwalk_version",
    "started_datetime",
    "startup_crash",
    "startup_time",
    "submitted_from",
    "system_memory_use_percentage",
    "throttleable",
    "topmost_filenames",
    "total_page_file",
    "total_physical_memory",
    "total_virtual_memory",
    "upload_file_minidump_browser",
    "upload_file_minidump_browser.json_dump",
    "upload_file_minidump_browser.json_dump.crash_info",
    "upload_file_minidump_browser.json_dump.crash_info.address",
    "upload_file_minidump_browser.json_dump.crash_info.assertion",
    "upload_file_minidump_browser.json_dump.crash_info.crashing_thread",
    "upload_file_minidump_browser.json_dump.crash_info.type",
    "upload_file_minidump_browser.json_dump.crashing_thread",
    "upload_file_minidump_browser.json_dump.crashing_thread.frame_count",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[]",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].file",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].frame",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].function",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].function_offset",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].line",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].missing_symbols",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].module",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].module_offset",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].offset",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].registers",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].registers.(re:^.+$)",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].trust",
    "upload_file_minidump_browser.json_dump.crashing_thread.last_error_value",
    "upload_file_minidump_browser.json_dump.crashing_thread.thread_name",
    "upload_file_minidump_browser.json_dump.crashing_thread.threads_index",
    "upload_file_minidump_browser.json_dump.lsb_release",
    "upload_file_minidump_browser.json_dump.lsb_release.codename",
    "upload_file_minidump_browser.json_dump.lsb_release.description",
    "upload_file_minidump_browser.json_dump.lsb_release.id",
    "upload_file_minidump_browser.json_dump.lsb_release.release",
    "upload_file_minidump_browser.json_dump.mac_crash_info",
    "upload_file_minidump_browser.json_dump.mac_crash_info.num_records",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[]",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].abort_cause",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].backtrace",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].dialog_mode",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].message",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].message2",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].module",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].signature_string",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].thread",
    "upload_file_minidump_browser.json_dump.modules",
    "upload_file_minidump_browser.json_dump.modules.[]",
    "upload_file_minidump_browser.json_dump.modules.[].base_addr",
    "upload_file_minidump_browser.json_dump.modules.[].cert_subject",
    "upload_file_minidump_browser.json_dump.modules.[].code_id",
    "upload_file_minidump_browser.json_dump.modules.[].corrupt_symbols",
    "upload_file_minidump_browser.json_dump.modules.[].debug_file",
    "upload_file_minidump_browser.json_dump.modules.[].debug_id",
    "upload_file_minidump_browser.json_dump.modules.[].end_addr",
    "upload_file_minidump_browser.json_dump.modules.[].filename",
    "upload_file_minidump_browser.json_dump.modules.[].loaded_symbols",
    "upload_file_minidump_browser.json_dump.modules.[].missing_symbols",
    "upload_file_minidump_browser.json_dump.modules.[].symbol_url",
    "upload_file_minidump_browser.json_dump.modules.[].version",
    "upload_file_minidump_browser.json_dump.modules_contains_cert_info",
    "upload_file_minidump_browser.json_dump.pid",
    "upload_file_minidump_browser.json_dump.status",
    "upload_file_minidump_browser.json_dump.system_info",
    "upload_file_minidump_browser.json_dump.system_info.cpu_arch",
    "upload_file_minidump_browser.json_dump.system_info.cpu_count",
    "upload_file_minidump_browser.json_dump.system_info.cpu_info",
    "upload_file_minidump_browser.json_dump.system_info.cpu_microcode_version",
    "upload_file_minidump_browser.json_dump.system_info.os",
    "upload_file_minidump_browser.json_dump.system_info.os_ver",
    "upload_file_minidump_browser.json_dump.thread_count",
    "upload_file_minidump_browser.json_dump.threads",
    "upload_file_minidump_browser.json_dump.threads.[]",
    "upload_file_minidump_browser.json_dump.threads.[].frame_count",
    "upload_file_minidump_browser.json_dump.threads.[].frames",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[]",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].file",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].frame",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].function",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].function_offset",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].line",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].missing_symbols",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].module",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].module_offset",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].offset",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].registers",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].registers.(re:^.+$)",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].trust",
    "upload_file_minidump_browser.json_dump.threads.[].last_error_value",
    "upload_file_minidump_browser.json_dump.threads.[].thread_name",
    "upload_file_minidump_browser.mdsw_return_code",
    "upload_file_minidump_browser.mdsw_status_string",
    "upload_file_minidump_browser.stackwalk_version",
    "upload_file_minidump_browser.success",
    "uptime",
    "uptime_ts",
    "useragent_locale",
    "utility_process_sandboxing_kind",
    "uuid",
    "vendor",
    "version",
    "windows_error_reporting",
    "xpcom_spin_event_loop_stack",
}


def test_processed_crash_schema():
    # We use the schema reducer to traverse the schema and validate the socorro metadata
    # values

    metadata_schema = get_file_content("socorro_metadata.1.schema.yaml")

    public_fields = set()

    def validate_metadata(path, general_path, schema_item):
        # Print this out so it's clear which item failed
        if "socorro" in schema_item:
            try:
                jsonschema.validate(schema_item["socorro"], metadata_schema)
            except Exception:
                print(f"Exception validating {general_path}")
                raise

            permissions = schema_item["socorro"].get("permissions", [])

            # Make sure all fields have permissions set
            if not permissions:
                raise PermissionsMissingError(f"{general_path} is missing permissions")

            # Make sure all public fields have parents that are public--otherwise they
            # will get reduced out
            if "public" in permissions:
                # Add this field to the public_fields set
                public_fields.add(".".join(split_path(general_path)))

                parts = list(split_path(general_path))
                for i in range(len(parts)):
                    parent = ".".join(parts[:i])
                    if not parent:
                        continue

                    if parent not in public_fields:
                        raise NonPublicParentError(
                            f"{general_path} has non-public parent {parent}"
                        )

    traverse_schema(
        schema=PROCESSED_CRASH_SCHEMA,
        visitor_function=validate_metadata,
    )

    # Verify that the list of public fields is what we expect. This helps to alleviate
    # inadvertently making a field public that you didn't intend to make public.
    assert public_fields == KNOWN_PUBLIC_FIELDS
