from nose.tools import eq_, ok_
from django.test import TestCase

from crashstats import scrubber


class TestScrubber(TestCase):

    def test_scrub_string_email(self):
        data = 'this is my email me@example.org!'
        res = scrubber.scrub_string(data, scrubber.EMAIL)
        eq_(res, 'this is my email !')

    def test_scrub_string_url(self):
        data = 'this is my Web site http://example.org/?param=12 !'
        res = scrubber.scrub_string(data, scrubber.URL)
        eq_(res, 'this is my Web site  !')

        data = 'link www.example.org/?param=12'
        res = scrubber.scrub_string(data, scrubber.URL)
        eq_(res, 'link ')

    def test_scrub_dict_remove_fields(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        res = scrubber.scrub_dict(data, remove_fields=['email'])
        eq_(res, {'text': 'hello'})

    def test_scrub_dict_replace_fields(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        res = scrubber.scrub_dict(data, replace_fields=[('email', 'scrubbed')])
        eq_(res, {'email': 'scrubbed', 'text': 'hello'})

    def test_scrub_dict_clean_fields(self):
        data = {
            'email': 'me@example.org',
            'text': (
                'this is my email address me@example.org and my website '
                'http://www.example.org/ do you like it?'
            )
        }
        res = scrubber.scrub_dict(
            data,
            clean_fields=[('text', scrubber.EMAIL), ('text', scrubber.URL)]
        )
        ok_('email' in res)
        ok_('text' in res)
        ok_('email address' in res['text'])
        ok_('me@example.org' not in res['text'])
        ok_('http://www.example.org/' not in res['text'])

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
        res = scrubber.scrub_data(data)
        eq_(data, res)

        res = scrubber.scrub_data(
            data,
            remove_fields=['age'],
            replace_fields=[('email', 'NO EMAIL'), ('url', 'NO URL')],
            clean_fields=[('text', scrubber.EMAIL), ('text', scrubber.URL)]
        )
        eq_(len(res), 2)
        eq_(res[0]['email'], 'NO EMAIL')
        eq_(res[1]['url'], 'NO URL')
        ok_('age' not in res[0])
        ok_('age' not in res[1])
        ok_('www.example.org' not in res[0]['text'])
