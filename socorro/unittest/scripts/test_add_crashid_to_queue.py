# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from mock import MagicMock, patch
import pytest

from socorro.lib.ooid import create_new_ooid
from socorro.scripts.add_crashid_to_queue import (
    main,
)


def test_missing_args(capsys):
    # Make sure that running main with no args causes the script to exit with exit_code 2
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.exconly() == 'SystemExit: 2'

    # Make sure it prints some stuff to stdout
    out, err = capsys.readouterr()
    usage_text = (
        'usage: add_crashid_to_queue.py [-h] queue crashid [crashid ...]\n'
        'add_crashid_to_queue.py: error: too few arguments\n'
    )
    assert err == usage_text


def test_bad_crashid(capsys):
    exit_code = main(['socorro.normal', 'badcrashid'])
    assert exit_code == 1

    out, err = capsys.readouterr()
    assert out == 'Crash id "badcrashid" is not valid. Exiting.\n'


def test_publish(capsys):
    pika_path = 'socorro.scripts.add_crashid_to_queue.pika'
    with patch(pika_path) as mock_pika_module:
        conn = MagicMock()
        mock_pika_module.BlockingConnection.return_value = conn

        channel = MagicMock()
        conn.channel.return_value = channel

        crash_id = create_new_ooid()
        exit_code = main(['socorro.normal', crash_id])
        assert exit_code == 0

        # Assert the connection was created correctly
        assert mock_pika_module.ConnectionParameters.call_count == 1
        kwargs = mock_pika_module.ConnectionParameters.mock_calls[0][2]
        # FIXME(willkg): a better way might be to mock os.environ and then provide values that we
        # can assert with more confidence here
        assert kwargs['host'] == os.environ['resource.rabbitmq.host']
        assert kwargs['port'] == int(os.environ.get('resource.rabbitmq.port', '5672'))
        assert kwargs['virtual_host'] == os.environ['resource.rabbitmq.virtual_host']

        # Assert there was one call to basic_publish and check the important arguments which are
        # passed as kwargs
        assert channel.basic_publish.call_count == 1
        args, kwargs = channel.basic_publish.call_args

        assert kwargs['routing_key'] == 'socorro.normal'
        assert kwargs['body'] == crash_id
