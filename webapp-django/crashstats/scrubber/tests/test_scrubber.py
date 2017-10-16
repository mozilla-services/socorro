from crashstats.base.tests.testbase import TestCase
from crashstats import scrubber


class TestScrubber(TestCase):

    def test_scrub_string_email(self):
        data = 'this is my email me@example.org!'
        res = scrubber.scrub_string(data, scrubber.EMAIL)
        assert res == 'this is my email !'

    def test_scrub_string_url(self):
        data = 'this is my Web site http://example.org/?param=12 !'
        res = scrubber.scrub_string(data, scrubber.URL)
        assert res == 'this is my Web site  !'

        data = 'link www.example.org/?param=12'
        res = scrubber.scrub_string(data, scrubber.URL)
        assert res == 'link '

    def test_scrub_dict_remove_fields_in_place(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        scrubber.scrub_dict(data, remove_fields=['email'])
        assert data == {'text': 'hello'}

    def test_scrub_dict_remove_fields_copy(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        res = scrubber.scrub_dict(data, remove_fields=['email'],
                                  make_copy=True)
        assert res == {'text': 'hello'}
        assert 'email' in data
        assert 'text' in data

    def test_scrub_dict_replace_fields(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        res = scrubber.scrub_dict(data, replace_fields=[('email', 'scrubbed')])
        assert res == {'email': 'scrubbed', 'text': 'hello'}

    def test_scrub_dict_clean_fields(self):
        data = {
            'email': 'me@example.org',
            'text': (
                'this is my email address me@example.org and my website '
                'http://www.example.org/ do you like it?'
            )
        }
        scrubber.scrub_dict(
            data,
            clean_fields=[('text', scrubber.EMAIL), ('text', scrubber.URL)]
        )
        assert 'email' in data
        assert 'text' in data
        assert 'email address' in data['text']
        assert 'me@example.org' not in data['text']
        assert 'http://www.example.org/' not in data['text']

    def test_scrub_data(self):
        data = [
            {
                'email': 'me@example.org',
                'text': 'look at my site www.example.org it is cool',
                'age': 25,
            },
            {
                'email': None,
                'url': 'http://mozilla.org',
                'age': 25,
            }
        ]
        copy = data[:]
        scrubber.scrub_data(data)
        assert data == copy

        scrubber.scrub_data(
            data,
            remove_fields=['age'],
            replace_fields=[('email', 'NO EMAIL'), ('url', 'NO URL')],
            clean_fields=[('text', scrubber.EMAIL), ('text', scrubber.URL)]
        )
        assert len(data) == 2
        assert data[0]['email'] == 'NO EMAIL'
        assert data[1]['url'] == 'NO URL'
        assert 'age' not in data[0]
        assert 'age' not in data[1]
        assert 'www.example.org' not in data[0]['text']
