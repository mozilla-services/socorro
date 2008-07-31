<?php 
/* SVN FILE: $Id$ */
/* Frame Fixture generated on: 2008-07-30 17:07:18 : 1217463318*/

class FrameFixture extends CakeTestFixture {
	var $name = 'Frame';
	var $table = 'frames';
	var $fields = array(
			'report_id' => array('type'=>'integer', 'null' => false),
			'frame_num' => array('type'=>'integer', 'null' => false),
			'signature' => array('type'=>'string', 'null' => true),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'report_id'  => 1,
			'frame_num'  => 1,
			'signature'  => 'Lorem ipsum dolor sit amet'
			));
}
?>