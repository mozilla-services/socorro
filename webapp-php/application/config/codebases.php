<?php
// Mappings of source code types to web links
$config['vcsMappings'] = array(
    'cvs' => array( 
        'cvs.mozilla.org' => 
          'http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s' 
    ),
    'hg' => array( 
        'hg.mozilla.org' =>
	    'http://hg.mozilla.org/%(repo)s/annotate/%(revision)s/%(file)s#l%(line)s'
));
$config['bugTrackingUrl'] = 'https://bugzilla.mozilla.org/show_bug.cgi?id=';
?>
