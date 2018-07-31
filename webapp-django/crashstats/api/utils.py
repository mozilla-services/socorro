from crashstats.base.templatetags.jinja_helpers import is_dangerous_cpu
from crashstats.base.utils import urlencode_obj
from crashstats.crashstats.templatetags.jinja_helpers import (
    booleanish_to_boolean,
    human_readable_iso_date,
    show_duration,
    show_filesize,
    timestamp_to_date
)


def transform_report_details(report, raw_crash, crashing_thread, parsed_dump):
    report_data = {
        "uuid": report.get('uuid'),
        "signature": report.get('signature'),
        "dateProcessed": human_readable_iso_date(report.get('date_processed')),
        "uptime": show_duration(report.get('uptime')),
        'lastCrash': show_duration(report.get('last_crash'), 'seconds before submission'),
        "installAge": show_duration(
            report.get('install_age'),
            'seconds since version was first installed'
        ),
        "product": report.get('product'),
        "releaseChannel": report.get('release_channel'),
        "version": report.get('version'),
        "build": report.get('build'),
        "os": report.get('os_pretty_version') or report.get('os_name'),
        "osVersion": report.get('os_version'),
        "cpuName": report.get('cpu_name'),
        'cpuInfo': report.get('cpu_info'),
        "isDangerousCpu": is_dangerous_cpu(report.get('cpu_name'), report.get('cpu_info')),
        "processType": report.get('process_type'),
        "pluginName": report.get('PluginName'),
        "pluginVersion": report.get('PluginVersion'),
        "pluginFilename": report.get('PluginFilename'),
        "crashReason": report.get('reason'),
        "crashAddress": report.get('address'),
        "addonsChecked": report.get('addons_checked'),
        "app_notes": report.get('app_notes'),
        "processorNotes": report.get('processor_notes'),
    }
    raw_crash_data = {
        'installTime': timestamp_to_date(raw_crash.get('InstallTime')),
        "androidVersion": raw_crash.get('Android_Version'),
        "b2gOsVersion": raw_crash.get('B2G_OS_Version'),
        "androidManufacturer": raw_crash.get('Android_Manufacturer'),
        "androidModel": raw_crash.get('Android_Model'),
        "androidCpuAbi": raw_crash.get('Android_CPU_ABI'),
        "adapterVendorId": raw_crash.get('AdapterVendorID'),
        "adapterDeviceID": raw_crash.get('AdapterVendorID'),
        "statupCrash": raw_crash.get('StatupCrash'),
        "isStartupCrash": booleanish_to_boolean(raw_crash.get('StartupCrash')),
        "remoteType": raw_crash.get('RemoteType'),
        "flashProcessDump": raw_crash.get('FlashProcessDump'),
        "mozCrashReason": raw_crash.get('MozCrashReason'),
        'totalVirtualMemory': show_filesize(raw_crash.get('TotalVirtualMemory')),
        'availableVirtualMemory': show_filesize(raw_crash.get('AvailableVirtualMemory')),
        'availablePageFile': show_filesize(raw_crash.get('AvailablePageFile')),
        'availablePhysicalMemory': show_filesize(raw_crash.get('AvailablePhysicalMemory')),
        'oOMAllocationSize': show_filesize(raw_crash.get('OOMAllocationSize')),
        'javaStackTrace': raw_crash.get('JavaStackTrace'),
        'accessibility': raw_crash.get('Accessibility'),
    }
    memeory_measures_data = {}
    if 'memory_measures' in report:
        memeory_measures_data = {
            'memory_measures': show_filesize(report.memory_measures.explicit),
            'gfx_textures': show_filesize(report.memory_measures.gfx_textures),
            'ghost_windows': show_filesize(report.memory_measures.ghost_windows),
            'heap_allocated': show_filesize(report.memory_measures.heap_allocated),
            'heap_overhead': show_filesize(report.memory_measures.heap_overhead),
            'heap_unclassified': show_filesize(report.memory_measures.heap_unclassified),
            'host_object_urls': show_filesize(report.memory_measures.host_object_urls),
            'images': show_filesize(report.memory_measures.images),
            'js_main_runtime': show_filesize(report.memory_measures.js_main_runtime),
            'private': show_filesize(report.memory_measures.private),
            'resident': show_filesize(report.memory_measures.resident),
            'resident_unique': show_filesize(report.memory_measures.resident_unique),
            'system_heap_allocated': show_filesize(report.memory_measures.system_heap_allocated),
            'top_none_detached': show_filesize(report.memory_measures.top_none_detached),
            'vsize': show_filesize(report.memory_measures.vsize),
            'vsize_max_contiguous': show_filesize(report.memory_measures.vsize_max_contiguous),
        }
    thread_data = []
    if crashing_thread is not None:
        thread_data = [
            {
                "thread": thread.get('thread'),
                "name": thread.get('thread_name'),
                "frames": [
                    {
                        "frame": frame.get('frame'),
                        "isMissingSymbols": frame.get('missing_symbols'),
                        "module": frame.get('module'),
                        "signature": frame.get('signature'),
                        "sourceLink": frame.get('source_link'),
                        "file": frame.get('file'),
                        'line': frame.get('line'),
                    }
                    for frame in thread.get('frames')
                ]
            }
            for thread in parsed_dump.get('threads')
        ]

    query_string = urlencode_obj({"q": report.get('signature')})
    return {
        "report": report_data,
        "rawCrash": raw_crash_data,
        "memoryMeasures": memeory_measures_data,
        "crashingThread": crashing_thread,
        "threadData": thread_data,
        "sumoLink": 'https://support.mozilla.org/search?{}'.format(query_string),
        "mdnLink": 'https://developer.mozilla.org/en-US/docs/Understanding_crash_reports',
    }
