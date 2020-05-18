# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy

from configman.dotdict import DotDict
import pytest

from socorro.lib.util import dotdict_to_dict, retry, MaxAttemptsError


class Testdotdict_to_dict:
    def test_primitives(self):
        # Test all the primitives
        assert dotdict_to_dict(None) is None
        assert dotdict_to_dict([]) == []
        assert dotdict_to_dict("") == ""
        assert dotdict_to_dict(1) == 1
        assert dotdict_to_dict({}) == {}

    def test_complex(self):
        def comp(data, expected):
            # First dotdict_to_dict the data and compare it.
            new_dict = dotdict_to_dict(data)
            assert new_dict == expected

            # Now deepcopy the new dict to make sure it's ok.
            copy.deepcopy(new_dict)

        # dict -> dict
        comp({"a": 1}, {"a": 1})

        # outer dotdict -> dict
        comp(DotDict({"a": 1}), {"a": 1})

        # in a list
        comp({"a": 1, "b": [DotDict({"a": 2}), 3, 4]}, {"a": 1, "b": [{"a": 2}, 3, 4]})
        # mixed dotdicts
        comp(DotDict({"a": 1, "b": DotDict({"a": 2})}), {"a": 1, "b": {"a": 2}})


def make_fake_sleep():
    sleeps = []

    def _fake_sleep(attempt):
        sleeps.append(attempt)

    _fake_sleep.sleeps = sleeps
    return _fake_sleep


class Test_retry:
    """Tests for the retry decorator"""

    def test_retry_returns_correct_value(self):
        @retry()
        def some_thing():
            return 1

        assert some_thing() == 1

    def test_retryable_exceptions(self):
        # This will fail on the first attempt and raise MyException because MyException
        # is not in the list of retryable exceptions
        class MyException(Exception):
            pass

        fake_sleep = make_fake_sleep()

        @retry(retryable_exceptions=ValueError, sleep_function=make_fake_sleep)
        def some_thing():
            raise MyException

        with pytest.raises(MyException):
            some_thing()
        assert fake_sleep.sleeps == []

        # This will fail on the first attempt because MyException is not in the list of
        # retryable exceptions
        fake_sleep = make_fake_sleep()

        @retry(retryable_exceptions=[ValueError, IndexError], sleep_function=fake_sleep)
        def some_thing():
            raise MyException

        with pytest.raises(MyException):
            some_thing()
        assert fake_sleep.sleeps == []

        # This will retry until the max attempts and then raise MaxAttemptsError--the
        # actual exception is chained
        fake_sleep = make_fake_sleep()

        @retry(retryable_exceptions=ValueError, sleep_function=fake_sleep)
        def some_thing():
            raise ValueError

        with pytest.raises(MaxAttemptsError):
            some_thing()
        assert fake_sleep.sleeps == [2, 2, 2, 2, 2]

    def test_retryable_return(self):
        # Will keep retrying until max_attempts and then raise an error that includes
        # the last function return
        def is_not_200(ret):
            return ret != 200

        fake_sleep = make_fake_sleep()

        @retry(retryable_return=is_not_200, sleep_function=fake_sleep)
        def some_thing():
            return 404

        with pytest.raises(MaxAttemptsError) as excinfo:
            some_thing()

        assert excinfo.value.return_value == 404
        assert len(fake_sleep.sleeps) == 5

        # Will retry a couple of times
        fake_sleep = make_fake_sleep()

        def make_some_thing(fake_sleep):
            returns = [404, 404, 200]

            @retry(retryable_return=is_not_200, sleep_function=fake_sleep)
            def some_thing():
                return returns.pop(0)

            return some_thing

        some_thing = make_some_thing(fake_sleep)
        some_thing()
        assert fake_sleep.sleeps == [2, 2]

        # Will succeed and not retry because the return value is fine
        fake_sleep = make_fake_sleep()

        @retry(retryable_return=is_not_200, sleep_function=fake_sleep)
        def some_thing():
            return 200

        some_thing()
        assert fake_sleep.sleeps == []

    def test_retries_correct_number_of_times(self):
        fake_sleep = make_fake_sleep()

        @retry(sleep_function=fake_sleep)
        def some_thing():
            raise Exception

        with pytest.raises(Exception):
            some_thing()

        assert fake_sleep.sleeps == [2, 2, 2, 2, 2]

    def test_wait_time_generator(self):
        def waits():
            for i in [1, 1, 2, 2, 1, 1]:
                yield i

        fake_sleep = make_fake_sleep()

        @retry(wait_time_generator=waits, sleep_function=fake_sleep)
        def some_thing():
            raise Exception

        with pytest.raises(Exception):
            some_thing()
        assert fake_sleep.sleeps == [1, 1, 2, 2, 1, 1]
