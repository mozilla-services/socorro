# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib.util import retry, MaxAttemptsError


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
        assert fake_sleep.sleeps == [1, 1, 1, 1, 1]

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
        assert fake_sleep.sleeps == [1, 1]

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

        assert fake_sleep.sleeps == [1, 1, 1, 1, 1]

    def test_wait_time_generator(self):
        def waits():
            yield from [1, 1, 2, 2, 1, 1]

        fake_sleep = make_fake_sleep()

        @retry(wait_time_generator=waits, sleep_function=fake_sleep)
        def some_thing():
            raise Exception

        with pytest.raises(Exception):
            some_thing()
        assert fake_sleep.sleeps == [1, 1, 2, 2, 1, 1]
