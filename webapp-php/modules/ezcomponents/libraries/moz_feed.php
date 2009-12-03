<?php
require_once(Kohana::find_file('libraries/Feed', 'feed', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/interfaces', 'element', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/interfaces', 'processor', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/interfaces', 'parser', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'generator', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'id', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'text', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'date', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'person', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'entry', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/structs', 'link', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/processors', 'atom', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/processors', 'rss2', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Base/exceptions', 'exception', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/exceptions', 'exception', TRUE, 'php'));
require_once(Kohana::find_file('libraries/Feed/exceptions', 'meta_data_missing', TRUE, 'php'));

/**
 * Adapter between Socorro UI and eZ Components's Feed library
 */
function moz_feed($base_url, $feed_link, $title, $reports)
{
        $feed = new ezcFeed(); 
	$feed->id = $base_url . $feed_link;
	$feed->updated = date(DateTime::ATOM);
        $feed->title = $title;
        $feed->description = 'This feed contains the last 500 crash reports processed by crash stats.based on product, version, and operating system';

	$author = $feed->add( 'author' );
	$author->name = 'Socorro UI';
	#$author->email = 'nospam@ez.no'; 

	$link = $feed->add( 'link' );
	$link->href = $base_url . $feed_link; 

	foreach ($reports as $report) {
	  $report->url = '';
	  $item = $feed->add( 'item' ); 
	  $item->id = htmlentities($report->uuid);
	  $item->title = htmlentities($report->signature);
	  $item->description = htmlentities(
			           substr( 
				       // chops of 'stdClass Object (' and ') '
				       print_r($report, TRUE), 
				       17, -2)); 
	  $item->published = $item->updated = htmlentities($report->date_processed);

	  $link = $item->add( 'link' );
	  $link->title = 'Crash Report Details';
	  $link->href = $base_url . 'report/index/' . $report->uuid; 

	  $link = $item->add( 'link' );
	  $link->rel = 'alternate';
	  $link->type = 'application/x-gzip';
	  $link->title = 'Crash Report as gzip compressed JSON file';
	  $link->href = $base_url . 'dumps/' . htmlentities($report->uuid) . '.jsonz'; 
	}

	$feedXml = $feed->generate( 'atom' );
	return array('xml' => $feedXml,
		     'contentType' => $feed->getContentType());
}

?>