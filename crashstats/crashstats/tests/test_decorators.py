from django import http
from crashstats.crashstats import decorators
from unittest import TestCase
from django.test.client import RequestFactory


class TestCheckDays(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_basics(self):

        @decorators.check_days_parameter([1, 2], 2)
        def view(request):
            days = request.days
            return http.HttpResponse(str(10000 + days))

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.content, '10002')  # default

        request = self.factory.get('/', {'days': '1'})
        response = view(request)
        self.assertEqual(response.content, '10001')

        # not a number
        request = self.factory.get('/', {'days': 'xxx'})
        response = view(request)
        self.assertEqual(response.status_code, 400)

        # out of range
        request = self.factory.get('/', {'days': 3})
        response = view(request)
        self.assertEqual(response.status_code, 400)

    def test_no_default(self):
        # if no default is passed, it has to be one of list of days

        @decorators.check_days_parameter([1, 2])
        def view(request):
            days = request.days
            return http.HttpResponse(str(10000 + days))

        request = self.factory.get('/', {'days': 1})
        response = view(request)
        self.assertEqual(response.content, '10001')

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.status_code, 400)

    def test_none_default(self):

        @decorators.check_days_parameter([1, 2], default=None)
        def view(request):
            return http.HttpResponse(str(request.days))

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.content, 'None')

    def test_using_possible_days(self):

        @decorators.check_days_parameter([1, 2], 2)
        def view(request):
            return http.HttpResponse(str(request.possible_days))

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.content, str([1, 2]))
