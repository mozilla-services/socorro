# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import json
import os

from django.http import HttpResponse
from django.utils.encoding import smart_str

import pytest

from crashstats.crashstats import utils


@pytest.mark.parametrize(
    "data, expected",
    [
        (
            # Test function sanitizing and a file that uses the vcs_mapping.
            {
                "frame": 0,
                "module": "bad.dll",
                "function": "Func(A * a,B b)",
                "file": "hg:hg.m.org/repo/name:dname/fname:rev",
                "line": 576,
            },
            {
                "function": "Func(A* a, B b)",
                "short_signature": "Func",
                "line": 576,
                "source_link": "http://hg.m.org/repo/name/file/rev/dname/fname#l576",
                "file": "dname/fname",
                "frame": 0,
                "signature": "Func(A* a, B b)",
                "module": "bad.dll",
            },
        ),
        (
            # Now with a file that has VCS info but isn't in vcs_mappings.
            {
                "frame": 0,
                "module": "bad.dll",
                "function": "Func",
                "file": "git:git.m.org/repo/name:dname/fname:rev",
                "line": 576,
            },
            {
                "function": "Func",
                "short_signature": "Func",
                "line": 576,
                "file": "fname",
                "frame": 0,
                "signature": "Func",
                "module": "bad.dll",
            },
        ),
        (
            # Test with no VCS info at all.
            {
                "frame": 0,
                "module": "bad.dll",
                "function": "Func",
                "file": "/foo/bar/file.c",
                "line": 576,
            },
            {
                "function": "Func",
                "short_signature": "Func",
                "line": 576,
                "file": "/foo/bar/file.c",
                "frame": 0,
                "signature": "Func",
                "module": "bad.dll",
            },
        ),
        (
            # Test with no source info at all.
            {"frame": 0, "module": "bad.dll", "function": "Func"},
            {
                "function": "Func",
                "short_signature": "Func",
                "frame": 0,
                "signature": "Func",
                "module": "bad.dll",
            },
        ),
        (
            # Test with no function info.
            {"frame": 0, "module": "bad.dll", "module_offset": "0x123"},
            {
                "short_signature": "bad.dll@0x123",
                "frame": 0,
                "signature": "bad.dll@0x123",
                "module": "bad.dll",
                "module_offset": "0x123",
            },
        ),
        (
            # Test with no module info.
            {"frame": 0, "offset": "0x1234"},
            {
                "short_signature": "@0x1234",
                "frame": 0,
                "signature": "@0x1234",
                "offset": "0x1234",
            },
        ),
        (
            # Test with unloaded modules.
            {
                "frame": 0,
                "offset": "0x00007ff9a9e9e4df",
                "unloaded_modules": [
                    {
                        "module": "obs-virtualcam-module64.dll",
                        "offsets": ["0x000000000000e4df"],
                    },
                ],
            },
            {
                "short_signature": "(unloaded obs-virtualcam-module64.dll@0xe4df)",
                "frame": 0,
                "signature": "(unloaded obs-virtualcam-module64.dll@0xe4df)",
                "offset": "0x00007ff9a9e9e4df",
                "unloaded_modules": [
                    {
                        "module": "obs-virtualcam-module64.dll",
                        "offsets": ["0x000000000000e4df"],
                    },
                ],
            },
        ),
    ],
)
def test_enhance_frame(data, expected):
    vcs_mappings = {
        "hg": {
            "hg.m.org": (
                "http://hg.m.org/%(repo)s/file/%(revision)s/%(file)s#l%(line)s"
            )
        }
    }

    # NOTE(willkg): data is modified in-place
    utils.enhance_frame(data, vcs_mappings)
    assert data == expected


def test_enhance_frame_s3_generated_sources():
    """Test a specific case when the frame references a S3 vcs
    and the file contains a really long sha string"""
    original_frame = {
        "file": (
            "s3:gecko-generated-sources:36d62ce2ec2925f4a13e44fe534b246c23b"
            "4b3d5407884d3bbfc9b0d9aebe4929985935ae582704c06e994ece0d1e7652"
            "8ff1edf4543e400d0aaa8f7251b15ca/ipc/ipdl/PCompositorBridgeChild.cpp:"
        ),
        "frame": 22,
        "function": (
            "mozilla::layers::PCompositorBridgeChild::OnMessageReceived(IP"
            "C::Message const&)"
        ),
        "function_offset": "0xd9d",
        "line": 1495,
        "module": "XUL",
        "module_offset": "0x7c50bd",
        "normalized": "mozilla::layers::PCompositorBridgeChild::OnMessageReceived",
        "offset": "0x108b7b0bd",
        "short_signature": "mozilla::layers::PCompositorBridgeChild::OnMessageReceived",
        "signature": (
            "mozilla::layers::PCompositorBridgeChild::OnMessageReceived(IP"
            "C::Message const&)"
        ),
        "trust": "cfi",
    }
    # Remember, enhance_frame() mutates the dict.
    frame = copy.copy(original_frame)
    utils.enhance_frame(frame, {})
    # Because it can't find a mapping in 'vcs_mappings', the frame's
    # 'file', the default behavior is to extract just the file's basename.
    frame["file"] = "PCompositorBridgeChild.cpp"

    # Try again, now with 's3' in vcs_mappings.
    frame = copy.copy(original_frame)
    utils.enhance_frame(
        frame,
        {
            "s3": {
                "gecko-generated-sources": ("https://example.com/%(file)s#L-%(line)s")
            }
        },
    )
    # There's a new key in the frame now. This is what's used in the
    # <a href> in the HTML.
    assert frame["source_link"]
    expected = (
        "https://example.com/36d62ce2ec2925f4a13e44fe534b246c23b4b3d540788"
        "4d3bbfc9b0d9aebe4929985935ae582704c06e994ece0d1e76528ff1edf4543e4"
        "00d0aaa8f7251b15ca/ipc/ipdl/PCompositorBridgeChild.cpp#L-1495"
    )
    assert frame["source_link"] == expected

    # And that links text is the frame's 'file' but without the 128 char
    # sha.
    assert frame["file"] == "ipc/ipdl/PCompositorBridgeChild.cpp"


def test_enhance_json_dump():
    vcs_mappings = {
        "hg": {
            "hg.m.org": (
                "http://hg.m.org/%(repo)s/file/%(revision)s/%(file)s#l%(line)s"
            )
        }
    }

    actual = {
        "threads": [
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "bad.dll",
                        "function": "Func",
                        "file": "hg:hg.m.org/repo/name:dname/fname:rev",
                        "line": 576,
                    },
                    {
                        "frame": 1,
                        "module": "another.dll",
                        "function": "Func2",
                        "file": "hg:hg.m.org/repo/name:dname/fname:rev",
                        "line": 576,
                    },
                ]
            },
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "bad.dll",
                        "function": "Func",
                        "file": "hg:hg.m.org/repo/name:dname/fname:rev",
                        "line": 576,
                    },
                    {
                        "frame": 1,
                        "module": "another.dll",
                        "function": "Func2",
                        "file": "hg:hg.m.org/repo/name:dname/fname:rev",
                        "line": 576,
                    },
                ]
            },
        ]
    }
    utils.enhance_json_dump(actual, vcs_mappings)
    expected = {
        "threads": [
            {
                "thread": 0,
                "frames": [
                    {
                        "frame": 0,
                        "function": "Func",
                        "short_signature": "Func",
                        "line": 576,
                        "source_link": (
                            "http://hg.m.org/repo/name/file/rev/dname/fname#l576"
                        ),
                        "file": "dname/fname",
                        "signature": "Func",
                        "module": "bad.dll",
                    },
                    {
                        "frame": 1,
                        "module": "another.dll",
                        "function": "Func2",
                        "signature": "Func2",
                        "short_signature": "Func2",
                        "source_link": (
                            "http://hg.m.org/repo/name/file/rev/dname/fname#l576"
                        ),
                        "file": "dname/fname",
                        "line": 576,
                    },
                ],
            },
            {
                "thread": 1,
                "frames": [
                    {
                        "frame": 0,
                        "function": "Func",
                        "short_signature": "Func",
                        "line": 576,
                        "source_link": (
                            "http://hg.m.org/repo/name/file/rev/dname/fname#l576"
                        ),
                        "file": "dname/fname",
                        "signature": "Func",
                        "module": "bad.dll",
                    },
                    {
                        "frame": 1,
                        "module": "another.dll",
                        "function": "Func2",
                        "signature": "Func2",
                        "short_signature": "Func2",
                        "source_link": (
                            "http://hg.m.org/repo/name/file/rev/dname/fname#l576"
                        ),
                        "file": "dname/fname",
                        "line": 576,
                    },
                ],
            },
        ]
    }
    assert actual == expected


def test_find_crash_id():
    # A good string, no prefix
    input_str = "1234abcd-ef56-7890-ab12-abcdef130802"
    crash_id = utils.find_crash_id(input_str)
    assert crash_id == input_str

    # A good string, with prefix
    input_str = "bp-1234abcd-ef56-7890-ab12-abcdef130802"
    crash_id = utils.find_crash_id(input_str)
    assert crash_id == "1234abcd-ef56-7890-ab12-abcdef130802"

    # A good looking string but not a real day
    input_str = "1234abcd-ef56-7890-ab12-abcdef130230"  # Feb 30th 2013
    assert not utils.find_crash_id(input_str)
    input_str = "bp-1234abcd-ef56-7890-ab12-abcdef130230"
    assert not utils.find_crash_id(input_str)

    # A bad string, one character missing
    input_str = "bp-1234abcd-ef56-7890-ab12-abcdef12345"
    assert not utils.find_crash_id(input_str)

    # A bad string, one character not allowed
    input_str = "bp-1234abcd-ef56-7890-ab12-abcdef12345g"
    assert not utils.find_crash_id(input_str)

    # Close but doesn't end with 6 digits
    input_str = "f48e9617-652a-11dd-a35a-001a4bd43ed6"
    assert not utils.find_crash_id(input_str)

    # A random string that does not match
    input_str = "somerandomstringthatdoesnotmatch"
    assert not utils.find_crash_id(input_str)


def test_json_view_basic(rf):
    request = rf.get("/")

    def func(request):
        return {"one": "One"}

    func = utils.json_view(func)
    response = func(request)
    assert isinstance(response, HttpResponse)
    assert json.loads(response.content) == {"one": "One"}
    assert response.status_code == 200


def test_json_view_indented(rf):
    request = rf.get("/?pretty=print")

    def func(request):
        return {"one": "One"}

    func = utils.json_view(func)
    response = func(request)
    assert isinstance(response, HttpResponse)
    assert json.dumps({"one": "One"}, indent=2) == smart_str(response.content)
    assert response.status_code == 200


def test_json_view_already_httpresponse(rf):
    request = rf.get("/")

    def func(request):
        return HttpResponse("something")

    func = utils.json_view(func)
    response = func(request)
    assert isinstance(response, HttpResponse)
    assert smart_str(response.content) == "something"
    assert response.status_code == 200


def test_json_view_custom_status(rf):
    request = rf.get("/")

    def func(request):
        return {"one": "One"}, 403

    func = utils.json_view(func)
    response = func(request)
    assert isinstance(response, HttpResponse)
    assert json.loads(response.content) == {"one": "One"}
    assert response.status_code == 403


class TestRenderException:
    def test_basic(self):
        html = utils.render_exception("hi!")
        assert html == "<ul><li>hi!</li></ul>"

    def test_escaped(self):
        html = utils.render_exception("<hi>")
        assert html == "<ul><li>&lt;hi&gt;</li></ul>"

    def test_to_string(self):
        try:
            raise NameError("<hack>")
        except NameError as exc:
            html = utils.render_exception(exc)
        assert html == "<ul><li>&lt;hack&gt;</li></ul>"


class TestUtils:
    def test_SignatureStats(self):
        signature = {
            "count": 2,
            "term": "EMPTY: no crashing thread identified; ERROR_NO_MINIDUMP_HEADER",
            "facets": {
                "histogram_uptime": [{"count": 2, "term": 0}],
                "startup_crash": [{"count": 2, "term": "F"}],
                "cardinality_install_time": {"value": 1},
                "is_garbage_collecting": [],
                "process_type": [],
                "platform": [{"count": 2, "term": ""}],
            },
        }
        platforms = [
            {"short_name": "win", "name": "Windows"},
            {"short_name": "mac", "name": "Mac OS X"},
            {"short_name": "lin", "name": "Linux"},
            {"short_name": "unknown", "name": "Unknown"},
        ]
        signature_stats = utils.SignatureStats(
            signature=signature,
            rank=1,
            num_total_crashes=2,
            platforms=platforms,
            previous_signature=None,
        )

        assert signature_stats.rank == 1
        assert (
            signature_stats.signature_term
            == "EMPTY: no crashing thread identified; ERROR_NO_MINIDUMP_HEADER"
        )
        assert signature_stats.percent_of_total_crashes == 100.0
        assert signature_stats.num_crashes == 2
        assert signature_stats.num_crashes_per_platform == {
            "mac_count": 0,
            "lin_count": 0,
            "win_count": 0,
        }
        assert signature_stats.num_crashes_in_garbage_collection == 0
        assert signature_stats.num_installs == 1
        assert signature_stats.num_crashes == 2
        assert signature_stats.num_startup_crashes == 0
        assert signature_stats.is_startup_crash == 0
        assert signature_stats.is_potential_startup_crash == 0
        assert signature_stats.is_startup_window_crash is True
        assert signature_stats.is_plugin_crash is False


SAMPLE_FILE_PCI_IDS = os.path.join(os.path.dirname(__file__), "sample_pci.ids")


def test_string_hex_to_hex_string():
    func = utils.string_hex_to_hex_string
    assert func("919A") == "0x919a"
    assert func("0x919A") == "0x919a"

    assert func("221") == "0x0221"
    assert func("0221") == "0x0221"
    assert func("0x0221") == "0x0221"


def test_parse_graphics_devices_iterable__pci_ids():
    with open(SAMPLE_FILE_PCI_IDS) as fp:
        lines = fp.readlines()
        devices = list(utils.pci_ids__parse_graphics_devices_iterable(lines))

        assert devices == [
            {
                "adapter_hex": "0x8139",
                "adapter_name": "AT-2500TX V3 Ethernet",
                "vendor_hex": "0x0010",
                "vendor_name": "Allied Telesis, Inc",
            },
            {
                "adapter_hex": "0x0001",
                "adapter_name": "PCAN-PCI CAN-Bus controller",
                "vendor_hex": "0x001c",
                "vendor_name": "PEAK-System Technik GmbH",
            },
            {
                "adapter_hex": "0x0004",
                "adapter_name": "2 Channel CAN Bus SJC1000",
                "vendor_hex": "0x001c",
                "vendor_name": "PEAK-System Technik GmbH",
            },
            {
                "adapter_hex": "0x0005",
                "adapter_name": "2 Channel CAN Bus SJC1000 (Optically Isolated)",
                "vendor_hex": "0x001c",
                "vendor_name": "PEAK-System Technik GmbH",
            },
            {
                "adapter_hex": "0x7801",
                "adapter_name": "WinTV HVR-1800 MCE",
                "vendor_hex": "0x0070",
                "vendor_name": "Hauppauge computer works Inc.",
            },
            {
                "adapter_hex": "0x0680",
                "adapter_name": "Ultra ATA/133 IDE RAID CONTROLLER CARD",
                "vendor_hex": "0x0095",
                "vendor_name": "Silicon Image, Inc. (Wrong ID)",
            },
        ]


@pytest.mark.parametrize(
    "raw, processed, expected",
    [
        # Missing data cases
        ({}, {}, []),
        ({}, {"addons": []}, []),
        ({"TelemetryEnvironment": "{}"}, {"addons": []}, []),
        # TelemetryEnvironment with bad JSON
        (
            {"TelemetryEnvironment": "{foo"},
            {"addons": ["someid:5.0"]},
            [utils.Addon(id="someid", version="5.0")],
        ),
        # Valid data
        (
            {
                "TelemetryEnvironment": json.dumps(
                    {
                        "addons": {
                            "activeAddons": {
                                "someid": {
                                    "version": "5.0",
                                    "scope": 1,
                                    "type": "extension",
                                    "updateDay": 18140,
                                    "isSystem": False,
                                    "isWebExtension": True,
                                    "multiprocessCompatible": True,
                                    "blocklisted": False,
                                    "description": "this is an addon",
                                    "name": "Some Addon",
                                    "userDisabled": False,
                                    "appDisabled": False,
                                    "foreignInstall": False,
                                    "hasBinaryComponents": False,
                                    "installDay": 18140,
                                    "signedState": 2,
                                },
                            }
                        }
                    }
                )
            },
            {"addons": ["someid:5.0"]},
            [
                utils.Addon(
                    id="someid",
                    version="5.0",
                    name="Some Addon",
                    is_system=False,
                    signed_state=2,
                )
            ],
        ),
    ],
)
def test_enhance_addons(raw, processed, expected):
    assert utils.enhance_addons(raw, processed) == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        # Don't drop non-beta numbers
        ("113.0a1", "113.0a1"),
        # Drop beta numbers
        ("113.0b5", "113.0b"),
        ("113.0b11", "113.0b"),
    ],
)
def test_drop_beta_num(data, expected):
    assert utils.drop_beta_num(data) == expected
