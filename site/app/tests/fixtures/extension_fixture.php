<?php 
/* SVN FILE: $Id$ */
/* Extension Fixture generated on: 2008-07-30 17:07:53 : 1217463173*/

class ExtensionFixture extends CakeTestFixture {
	var $name = 'Extension';
	var $table = 'extensions';
	var $fields = array(
			'report_id' => array('type'=>'integer', 'null' => false),
			'extension_key' => array('type'=>'integer', 'null' => false),
			'extension_id' => array('type'=>'string', 'null' => false, 'length' => 100),
			'extension_version' => array('type'=>'string', 'null' => true, 'length' => 16),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'report_id'  => 1,
			'extension_key'  => 1,
			'extension_id'  => 'Lorem ipsum dolor sit amet',
			'extension_version'  => 'Lorem ipsum do'
			));
}
?>