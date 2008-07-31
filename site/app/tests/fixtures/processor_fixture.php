<?php 
/* SVN FILE: $Id$ */
/* Processor Fixture generated on: 2008-07-30 17:07:23 : 1217463023*/

class ProcessorFixture extends CakeTestFixture {
	var $name = 'Processor';
	var $table = 'processors';
	var $fields = array(
			'id' => array('type'=>'integer', 'null' => false, 'default' => NULL, 'length' => 11, 'key' => 'primary'),
			'name' => array('type'=>'string', 'null' => false),
			'startdatetime' => array('type'=>'datetime', 'null' => false),
			'lastseendatetime' => array('type'=>'datetime', 'null' => true),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'id'  => 1,
			'name'  => 'Lorem ipsum dolor sit amet',
			'startdatetime'  => '2008-07-30 17:10:23',
			'lastseendatetime'  => '2008-07-30 17:10:23'
			));
}
?>