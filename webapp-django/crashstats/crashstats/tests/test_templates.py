from django.template.loader import render_to_string

from crashstats.base.tests.testbase import DjangoTestCase


class TestBugzillaComment(DjangoTestCase):
    def frame(
        self,
        frame=1,
        module='fake_module',
        signature='fake_signature',
        file='fake.cpp',
        line=1,
    ):
        return {
            'frame': frame,
            'module': module,
            'signature': signature,
            'file': file,
            'line': line,
        }

    def thread(self, frames=None):
        return {
            'frames': frames or []
        }

    def dump(self, threads=None):
        return {
            'threads': threads or []
        }

    def test_basic(self):
        parsed_dump = self.dump(threads=[
            self.thread(),  # Empty thread 0
            self.thread(frames=[
                self.frame(frame=0),
                self.frame(frame=1),
                self.frame(frame=2),
            ]),
        ])
        result = render_to_string('crashstats/bugzilla_comment.txt', {
            'uuid': 'test_uuid',
            'parsed_dump': parsed_dump,
            'crashing_thread': 1,
        })

        assert 'bp-test_uuid' in result
        assert 'Top 10 frames of crashing thread:' in result

        frame1 = parsed_dump['threads'][1]['frames'][1]
        assert '1 {module} {signature} {file}:{line}'.format(**frame1) in result

    def test_no_threads(self):
        """If parsed_dump has no threads available, do not output any
        frames.

        """
        result = render_to_string('crashstats/bugzilla_comment.txt', {
            'uuid': 'test',
            'parsed_dump': {},
        })
        assert 'Top 10 frames of crashing thread:' not in result

    def test_more_than_ten_frames(self):
        """If the crashing thread has more than ten frames, only display
        the top ten.

        """
        parsed_dump = self.dump(threads=[
            self.thread(frames=[self.frame(frame=frame) for frame in range(10)] + [
                self.frame(frame=10, module='do_not_include')
            ])
        ])
        result = render_to_string('crashstats/bugzilla_comment.txt', {
            'uuid': 'test_uuid',
            'parsed_dump': parsed_dump,
            'crashing_thread': 0,
        })

        assert 'do_not_include' not in result

    def test_remove_arguments(self):
        """If a frame signature includes function arguments, remove
        them.

        """
        parsed_dump = self.dump(threads=[
            self.thread(frames=[
                self.frame(
                    frame=0,
                    module='test_module',
                    signature='foo::bar(char* x, int y)',
                    file='foo.cpp',
                    line=7,
                ),
            ])
        ])
        result = render_to_string('crashstats/bugzilla_comment.txt', {
            'uuid': 'test_uuid',
            'parsed_dump': parsed_dump,
            'crashing_thread': 0,
        })

        assert '0 test_module foo::bar foo.cpp:7' in result

    def test_missing_line(self):
        """If a frame signature is missing a line number, do not include
        it.

        """
        parsed_dump = self.dump(threads=[
            self.thread(frames=[
                self.frame(
                    frame=0,
                    module='test_module',
                    signature='foo::bar(char* x, int y)',
                    file='foo.cpp',
                    line=None,
                ),
            ])
        ])
        result = render_to_string('crashstats/bugzilla_comment.txt', {
            'uuid': 'test_uuid',
            'parsed_dump': parsed_dump,
            'crashing_thread': 0,
        })

        assert '0 test_module foo::bar foo.cpp\n' in result

    def test_missing_file(self):
        """If a frame signature is missing file info, do not include it.

        """
        parsed_dump = self.dump(threads=[
            self.thread(frames=[
                self.frame(
                    frame=0,
                    module='test_module',
                    signature='foo::bar(char* x, int y)',
                    file=None,
                    line=None,
                ),
            ])
        ])
        result = render_to_string('crashstats/bugzilla_comment.txt', {
            'uuid': 'test_uuid',
            'parsed_dump': parsed_dump,
            'crashing_thread': 0,
        })

        assert '0 test_module foo::bar \n' in result
