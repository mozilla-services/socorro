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

    def test_scrub_dict_remove_fields_in_place(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        scrubber.scrub_dict(data, remove_fields=['email'])
        eq_(data, {'text': 'hello'})

    def test_scrub_dict_remove_fields_copy(self):
        data = {
            'email': 'me@example.org',
            'text': 'hello'
        }
        res = scrubber.scrub_dict(data, remove_fields=['email'],
                                  make_copy=True)
        eq_(res, {'text': 'hello'})
        ok_('email' in data)
        ok_('text' in data)

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
        scrubber.scrub_dict(
            data,
            clean_fields=[('text', scrubber.EMAIL), ('text', scrubber.URL)]
        )
        ok_('email' in data)
        ok_('text' in data)
        ok_('email address' in data['text'])
        ok_('me@example.org' not in data['text'])
        ok_('http://www.example.org/' not in data['text'])

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
        eq_(data, copy)

        scrubber.scrub_data(
            data,
            remove_fields=['age'],
            replace_fields=[('email', 'NO EMAIL'), ('url', 'NO URL')],
            clean_fields=[('text', scrubber.EMAIL), ('text', scrubber.URL)]
        )
        eq_(len(data), 2)
        eq_(data[0]['email'], 'NO EMAIL')
        eq_(data[1]['url'], 'NO URL')
        ok_('age' not in data[0])
        ok_('age' not in data[1])
        ok_('www.example.org' not in data[0]['text'])
