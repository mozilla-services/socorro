import humanfriendly

from crashstats.base.templatetags.jinja_helpers import is_dangerous_cpu
from crashstats.base.utils import urlencode_obj
from crashstats.crashstats.templatetags.jinja_helpers import (
    booleanish_to_boolean,
    human_readable_iso_date,
)


def transform_report_details(report, raw_crash, crashing_thread, parsed_dump, descriptions, user):
    report_data = {
        'addonsChecked': report.get('addons_checked'),
        'appNotes': report.get('app_notes'),
        'build': report.get('build'),
        'cpuInfo': report.get('cpu_info'),
        'cpuName': report.get('cpu_name'),
        'crashAddress': report.get('address'),
        'crashReason': report.get('reason'),
        'dateProcessed': human_readable_iso_date(report.get('date_processed')),
        'installAge': get_duration_data(report.get('install_age')),
        'isDangerousCpu': is_dangerous_cpu(report.get('cpu_name'), report.get('cpu_info')),
        'lastCrash': get_duration_data(report.get('last_crash')),
        'os': report.get('os_pretty_version') or report.get('os_name'),
        'osVersion': report.get('os_version'),
        'pluginFilename': report.get('PluginFilename'),
        'pluginName': report.get('PluginName'),
        'pluginVersion': report.get('PluginVersion'),
        'processorNotes': report.get('processor_notes'),
        'processType': report.get('process_type'),
        'product': report.get('product'),
        'releaseChannel': report.get('release_channel'),
        'signature': report.get('signature'),
        'uptime': get_duration_data(report.get('uptime')),
        'uuid': report.get('uuid'),
        'version': report.get('version'),
    }
    raw_crash_data = {
        'accessibility': raw_crash.get('Accessibility'),
        'adapterDeviceId': raw_crash.get('AdapterDeviceID'),
        'adapterVendorId': raw_crash.get('AdapterVendorID'),
        'androidCpuAbi': raw_crash.get('Android_CPU_ABI'),
        'androidManufacturer': raw_crash.get('Android_Manufacturer'),
        'androidModel': raw_crash.get('Android_Model'),
        'androidVersion': raw_crash.get('Android_Version'),
        'availablePageFile': get_filesize_data(raw_crash.get('AvailablePageFile')),
        'availablePhysicalMemory': get_filesize_data(raw_crash.get('AvailablePhysicalMemory')),
        'availableVirtualMemory': get_filesize_data(raw_crash.get('AvailableVirtualMemory')),
        'b2gOsVersion': raw_crash.get('B2G_OS_Version'),
        'flashProcessDump': raw_crash.get('FlashProcessDump'),
        'installTime': raw_crash.get('InstallTime'),
        'isStartupCrash': booleanish_to_boolean(raw_crash.get('StartupCrash')),
        'javaStackTrace': raw_crash.get('JavaStackTrace'),
        'mozCrashReason': raw_crash.get('MozCrashReason'),
        'oomAllocationSize': get_filesize_data(raw_crash.get('OOMAllocationSize')),
        'remoteType': raw_crash.get('RemoteType'),
        'statupCrash': raw_crash.get('StatupCrash'),
        'systemMemoryUsePercentage': raw_crash.get('SystemMemoryUsePercentage'),
        'totalVirtualMemory': get_filesize_data(raw_crash.get('TotalVirtualMemory')),
    }
    memeory_measures_data = {}
    if 'memory_measures' in report:
        memeory_measures_data = {
            'gfxTextures': get_filesize_data(report.memory_measures.gfx_textures),
            'ghostWindows': get_filesize_data(report.memory_measures.ghost_windows),
            'heapAllocated': get_filesize_data(report.memory_measures.heap_allocated),
            'heapOverhead': get_filesize_data(report.memory_measures.heap_overhead),
            'heapUnclassified': get_filesize_data(report.memory_measures.heap_unclassified),
            'hostObjectUrls': get_filesize_data(report.memory_measures.host_object_urls),
            'images': get_filesize_data(report.memory_measures.images),
            'jsMainRuntime': get_filesize_data(report.memory_measures.js_main_runtime),
            'memeoryMeasures': get_filesize_data(report.memory_measures.explicit),
            'private': get_filesize_data(report.memory_measures.private),
            'resident': get_filesize_data(report.memory_measures.resident),
            'residentUnique': get_filesize_data(report.memory_measures.resident_unique),
            'systemHeapAllocated': get_filesize_data(report.memory_measures.system_heap_allocated),
            'topNoneAttached': get_filesize_data(report.memory_measures.top_none_detached),
            'vsize': get_filesize_data(report.memory_measures.vsize),
            'vsizeMaxContiguous': get_filesize_data(report.memory_measures.vsize_max_contiguous),
        }
    threads_data = []
    if crashing_thread is not None:
        threads_data = [
            {
                'thread': thread.get('thread'),
                'name': thread.get('thread_name'),
                'frames': [
                    {
                        'frame': frame.get('frame'),
                        'isMissingSymbols': frame.get('missing_symbols'),
                        'module': frame.get('module'),
                        'signature': frame.get('signature'),
                        'sourceLink': frame.get('source_link'),
                        'file': frame.get('file'),
                        'line': frame.get('line'),
                    }
                    for frame in thread.get('frames')
                ]
            }
            for thread in parsed_dump.get('threads')
        ]
    descriptions_data = {
        'report': {
            'addonsChecked': descriptions.get('processed_crash.addons_checked'),
            'appNotes': descriptions.get('processed_crash.app_notes'),
            'build': descriptions.get('processed_crash.build'),
            'cpuInfo': descriptions.get('processed_crash.cpu_info'),
            'cpuName': descriptions.get('processed_crash.cpu_name'),
            'crashAddress': descriptions.get('processed_crash.address'),
            'crashReason': descriptions.get('processed_crash.reason'),
            'dateProcessed': descriptions.get('processed_crash.date_processed'),
            'email': descriptions.get('processed_crash.email'),
            'exploitability': descriptions.get('processed_crash.exploitability'),
            'installAge': descriptions.get('processed_crash.install_age'),
            'lastCrash': descriptions.get('processed_crash.last_crash'),
            'os': descriptions.get('processed_crash.os_pretty_version'),
            'osVersion': descriptions.get('processed_crash.os_version'),
            'processType': descriptions.get('processed_crash.process_type'),
            'processorNotes': descriptions.get('processed_crash.processor_notes'),
            'product': descriptions.get('processed_crash.product'),
            'releaseChannel': descriptions.get('processed_crash.release_channel'),
            'signature': descriptions.get('processed_crash.signature'),
            'uptime': descriptions.get('processed_crash.uptime'),
            'url': descriptions.get('processed_crash.url'),
            'userComments': descriptions.get('processed_crash.user_comments'),
            'uuid': descriptions.get('processed_crash.uuid'),
            'version': descriptions.get('processed_crash.version'),
        },
        'rawCrash': {
            'accessibility': descriptions.get('raw_crash.Accessibility'),
            'adapterDeviceId': descriptions.get('raw_crash.AdapterDeviceID'),
            'adapterVendorId': descriptions.get('raw_crash.AdapterVendorID'),
            'androidCpuAbi': descriptions.get('raw_crash.Android_CPU_ABI'),
            'androidManufacturer': descriptions.get('raw_crash.Android_Manufacturer'),
            'androidModel': descriptions.get('raw_crash.Android_Model'),
            'androidVersion': descriptions.get('raw_crash.Android_Version'),
            'availablePageFile': descriptions.get('raw_crash.AvailablePageFile'),
            'availablePhysicalMemory': descriptions.get('raw_crash.AvailablePhysicalMemory'),
            'availableVirtualMemory': descriptions.get('raw_crash.AvailableVirtualMemory'),
            'b2gOsVersion': descriptions.get('raw_crash.B2G_OS_Version'),
            'flashProcessDump': descriptions.get('raw_crash.FlashProcessDump'),
            'installTime': descriptions.get('raw_crash.InstallTime'),
            'isStartupCrash': descriptions.get('raw_crash.StartupCrash'),
            'javaStackTrace': descriptions.get('processed_crash.java_stack_trace'),
            'mozCrashReason': descriptions.get('raw_crash.MozCrashReason'),
            'oomAllocationSize': descriptions.get('raw_crash.OOMAllocationSize'),
            'systemMemoryUsePercentage': descriptions.get('raw_crash.SystemMemoryUsePercentage'),
            'totalVirtualMemory': descriptions.get('raw_crash.TotalVirtualMemory'),
        },
    }
    is_your_crash = user.is_active and raw_crash.get('Email') == user.email
    sensitive_data = {'isYourCrash': is_your_crash}
    if is_your_crash or user.has_perm('crashstats.view_exploitability'):
        sensitive_data['exploitability'] = report.exploitability
    if is_your_crash or user.has_perm('crashstats.view_pii'):
        sensitive_data['url'] = raw_crash.url
        sensitive_data['email'] = raw_crash.email
        sensitive_data['userComments'] = report.user_comments

    query_string = urlencode_obj({'q': report.get('signature')})
    return {
        'crashingThread': crashing_thread,
        'descriptions': descriptions_data,
        'mdnLink': 'https://developer.mozilla.org/en-US/docs/Understanding_crash_reports',
        'memoryMeasures': memeory_measures_data,
        'rawCrash': raw_crash_data,
        'report': report_data,
        'sensitive': sensitive_data,
        'sumoLink': 'https://support.mozilla.org/search?{}'.format(query_string),
        'threads': threads_data,
    }


def get_filesize_data(bytes):
    if bytes is None:
            return {}
    return {
        'formatted': format(int(bytes), ','),
        'bytes': bytes,
        'humanfriendly': humanfriendly.format_size(int(bytes))
    }


def get_duration_data(seconds):
    if seconds is None:
        return {}
    return {
        'formatted': format(int(seconds), ','),
        'seconds': seconds,
        'humanfriendly': humanfriendly.format_timespan(int(seconds)),
    }
