import os

from django.template import Template
from django_statsd.patches.utils import wrap


def key(name):
    if not name.endswith('.html'):
        return None
    return name.replace(os.sep, '.')[:-5]


def new_template_init(self, template_string, origin=None, name='unknown'):
    return wrap(self._old_init(template_string, origin, name),
                'template.{0}.parse'.format(key(name)))


def new_render(self, context):
    return wrap(self._old_render(context),
                'template.{0}.parse'.format(key(self.name)))

def patch():
    if getattr(Template, '__patched', False):
        return

    # Monkey patch Django
    Template.__patched = True

    # Patch __init__
    Template._old_init = Template.__init__
    Template.__init__ = new_template_init

    # Patch _render
    Template._old_render = Template._render
    Template._render = new_render

