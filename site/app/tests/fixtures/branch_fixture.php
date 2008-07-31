<?php 
/* SVN FILE: $Id$ */
/* Branch Fixture generated on: 2008-07-30 17:07:21 : 1217462961*/

class BranchFixture extends CakeTestFixture {
	var $name = 'Branch';
	var $table = 'branches';
	var $fields = array(
			'product' => array('type'=>'string', 'null' => false, 'length' => 30),
			'version' => array('type'=>'string', 'null' => false, 'length' => 16),
			'branch' => array('type'=>'string', 'null' => false, 'length' => 24),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'product'  => 'Lorem ipsum dolor sit amet',
			'version'  => 'Lorem ipsum do',
			'branch'  => 'Lorem ipsum dolor sit '
			));
}
?>