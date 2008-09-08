<?php
/**
 * Application-specific settings separate from installation concerns.
 */

$config['dumpIDPrefix'] = 'bp-';

// Mappings of source code types to web links
$config['vcsMappings'] = array(
    'cvs' => array( 
        'cvs.mozilla.org/cvsroot' => 
          'http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s' 
    ),
    'hg' => array( 
        'hg.mozilla.org/mozilla-central' => 
            'http://hg.mozilla.org/mozilla-central/index.cgi/annotate/%(revision)s/%(file)s#l%(line)s' 
    )
);
