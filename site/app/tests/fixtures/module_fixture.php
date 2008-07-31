<?php 
/* SVN FILE: $Id$ */
/* Module Fixture generated on: 2008-07-30 17:07:41 : 1217463161*/

class ModuleFixture extends CakeTestFixture {
	var $name = 'Module';
	var $table = 'modules';
	var $fields = array(
			'report_id' => array('type'=>'integer', 'null' => false),
			'module_key' => array('type'=>'integer', 'null' => false),
			'filename' => array('type'=>'string', 'null' => false, 'length' => 40),
			'debug_id' => array('type'=>'string', 'null' => true, 'length' => 40),
			'module_version' => array('type'=>'string', 'null' => true, 'length' => 15),
			'debug_filename' => array('type'=>'string', 'null' => true, 'length' => 40),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'report_id'  => 1,
			'module_key'  => 1,
			'filename'  => 'Lorem ipsum dolor sit amet',
			'debug_id'  => 'Lorem ipsum dolor sit amet',
			'module_version'  => 'Lorem ipsum d',
			'debug_filename'  => 'Lorem ipsum dolor sit amet'
			));
}
?>