<?php
// Mappings of source code types to web links
$config['vcsMappings'] = array(
    'cvs' => array( 
        'cvs.mozilla.org/cvsroot' => 
          'http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s' 
    ),
    'hg' => array( 
        'hg.mozilla.org/mozilla-central' => 
	    'http://hg.mozilla.org/mozilla-central/index.cgi/annotate/%(revision)s/%(file)s#l%(line)s',
	'hg.mozilla.org/releases/mozilla-1.9.1' => 
	    'http://hg.mozilla.org/releases/mozilla-1.9.1/annotate/%(revision)s/%(file)s#l%(line)s',
	'hg.mozilla.org/releases/mozilla-1.9.2' => 
	    'http://hg.mozilla.org/releases/mozilla-1.9.2/annotate/%(revision)s/%(file)s#l%(line)s',
        'hg.mozilla.org/comm-central' =>
	    'http://hg.mozilla.org/comm-central/annotate/%(revision)s/%(file)s#l%(line)s',
        'hg.mozilla.org/releases/comm-1.9.1' =>
            'http://hg.mozilla.org/releases/comm-1.9.1/annotate/%(revision)s/%(file)s#l%(line)s'
));
$config['bugTrackingUrl'] = 'https://bugzilla.mozilla.org/show_bug.cgi?id=';
?>