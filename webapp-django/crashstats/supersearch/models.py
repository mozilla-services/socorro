import json

from crashstats import scrubber
from crashstats.crashstats import models

from . import forms


SUPERSEARCH_HITS_WHITELIST = (
    'additional_minidumps',
    'addons',
    'addons_checked',
    'address',
    'app_notes',
    'build_id',
    'client_crash_date',
    'completeddatetime',
    'cpu_info',
    'cpu_name',
    'crashedThread',
    'crash_time',
    'date',
    'distributor',
    'distributor_version',
    'flash_version',
    'hangid',
    'hang_type',
    'id',
    'install_age',
    'java_stack_trace',
    'last_crash',
    'platform',
    'platform_version',
    'plugin_filename',
    'plugin_name',
    'plugin_version',
    'processor_notes',
    'process_type',
    'product',
    'productid',
    'reason',
    'release_channel',
    'ReleaseChannel',
    'signature',
    'startedDateTime',
    'success',
    'topmost_filenames',
    'truncated',
    'uptime',
    'user_comments',
    'uuid',
    'version',
    'winsock_lsp',
    'accessibility',
    'adapter_device_id',
    'adapter_vendor_id',
    'android_board',
    'android_brand',
    'android_cpu_abi',
    'android_cpu_abi2',
    'android_device',
    'android_display',
    'android_fingerprint',
    'android_hardware',
    'android_manufacturer',
    'android_model',
    'android_version',
    'async_shutdown_timeout',
    'available_page_file',
    'available_physical_memory',
    'available_virtual_memory',
    'b2g_os_version',
    'bios_manufacturer',
    'cpu_usage_flash_process1',
    'cpu_usage_flash_process2',
    'dom_ipc_enabled',
    'em_check_compatibility',
    'frame_poison_base',
    'frame_poison_size',
    'is_garbage_collecting',
    'min_arm_version',
    'number_of_processors',
    'oom_allocation_size',
    'plugin_cpu_usage',
    'plugin_hang',
    'plugin_hang_ui_duration',
    'startup_time',
    'system_memory_use_percentage',
    'theme',
    'throttleable',
    'total_virtual_memory',
    'vendor',
    'additional_minidumps',
    'throttle_rate',
    'useragent_locale',
    # deliberately not including:
    #    email
    #    url
    #    exploitability
)


class SuperSearch(models.SocorroMiddleware):

    URL_PREFIX = '/supersearch/'

    API_WHITELIST = {
        'hits': SUPERSEARCH_HITS_WHITELIST
    }

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )

    # Generate the list of possible parameters from the associated form.
    # This way we only manage one list of parameters.
    possible_params = tuple(
        x for x in forms.SearchForm([], [], [], False, False).fields
    ) + (
        '_facets',
        '_results_offset',
        '_results_number',
        '_return_query',
    )


class SuperSearchUnredacted(SuperSearch):

    API_WHITELIST = {
        'hits': SUPERSEARCH_HITS_WHITELIST + (
            'email',
            'exploitability',
            'url',
        )
    }

    API_CLEAN_SCRUB = None

    API_REQUIRED_PERMISSIONS = (
        'crashstats.view_exploitability',
        'crashstats.view_pii'
    )

    # Generate the list of possible parameters from the associated form.
    # This way we only manage one list of parameters.
    possible_params = tuple(
        x for x in forms.SearchForm([], [], [], True, True).fields
    ) + (
        '_facets',
        '_results_offset',
        '_results_number',
        '_return_query',
    )


class Query(models.SocorroMiddleware):
    # No API_WHITELIST because this can't be accessed through the public API.

    URL_PREFIX = '/query/'

    required_params = (
        'query',
    )

    possible_params = (
        'indices',
    )

    def get(self, **kwargs):
        params = self.kwargs_to_params(kwargs)
        payload = {
            'query': json.dumps(params['query']),
            'indices': params.get('indices'),
        }
        return self.post(self.URL_PREFIX, payload)
