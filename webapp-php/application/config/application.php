<?php
/**
 * Application-specific settings separate from installation concerns.
 */

/** 
 * Returned to the client with a uuid following
 */
$config['dumpIDPrefix'] = 'bp-';

$config['vcsMappings'] = array(
    'cvs' => array(
        'cvs.mozilla.org/cvsroot' => 'http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s'
    )
);
