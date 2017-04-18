#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import xml.etree.ElementTree as ET

import requests

_BASE = 'https://webqa-ci.mozilla.com'
STAGE = _BASE + '/view/Socorro/job/socorro.stage/rssAll'
PROD = _BASE + '/view/Socorro/job/socorro.prod/rssAll'


def colored(text, color):
    RESET = '\033[0m'
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        COLORS = dict(
            zip(
                [
                    'grey',
                    'red',
                    'green',
                    'yellow',
                    'blue',
                    'magenta',
                    'cyan',
                    'white',
                ],
                range(30, 38)
            )
        )
        fmt_str = '\033[%dm%s'
        text = fmt_str % (COLORS[color], text)
        text += RESET
    return text


def run():
    errors = 0
    for url, name in ((STAGE, 'STAGE'), (PROD, 'PROD')):
        print name, u'⏱'
        xml = requests.get(url).text
        root = ET.fromstring(xml)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
        }
        for entry in root.findall('atom:entry', ns):
            for title in entry.findall('atom:title', ns):
                if 'broken' in title.text:
                    print u'💔 ',
                    print colored('BROKEN!', 'red')
                    errors += 1
                else:
                    print u'👍 ',
                    print colored(
                        'Ahhhh, everything seems to be fine.',
                        'green'
                    )
                print "({})".format(title.text)

            for link in entry.findall('atom:link', ns):
                print link.attrib['href']
            break

        print
    return errors


if __name__ == '__main__':
    import sys
    sys.exit(run())
