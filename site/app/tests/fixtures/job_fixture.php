<?php 
/* SVN FILE: $Id$ */
/* Job Fixture generated on: 2008-07-30 17:07:12 : 1217463432*/

class JobFixture extends CakeTestFixture {
	var $name = 'Job';
	var $table = 'jobs';
	var $fields = array(
			'id' => array('type'=>'integer', 'null' => false, 'default' => NULL, 'length' => 11, 'key' => 'primary'),
			'pathname' => array('type'=>'string', 'null' => false, 'length' => 1024),
			'uuid' => array('type'=>'string', 'null' => false, 'length' => 50),
			'owner' => array('type'=>'integer', 'null' => true),
			'priority' => array('type'=>'integer', 'null' => true, 'default' => '0'),
			'queueddatetime' => array('type'=>'datetime', 'null' => true),
			'starteddatetime' => array('type'=>'datetime', 'null' => true),
			'completeddatetime' => array('type'=>'datetime', 'null' => true),
			'success' => array('type'=>'boolean', 'null' => true),
			'message' => array('type'=>'text', 'null' => true, 'length' => 1073741824),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'id'  => 1,
			'pathname'  => 'Lorem ipsum dolor sit amet',
			'uuid'  => 'Lorem ipsum dolor sit amet',
			'owner'  => 1,
			'priority'  => 1,
			'queueddatetime'  => '2008-07-30 17:17:12',
			'starteddatetime'  => '2008-07-30 17:17:12',
			'completeddatetime'  => '2008-07-30 17:17:12',
			'success'  => 1,
			'message'  => 'Lorem ipsum dolor sit amet, aliquet feugiat. Convallis morbi fringilla gravida,
									phasellus feugiat dapibus velit nunc, pulvinar eget sollicitudin venenatis cum nullam,
									vivamus ut a sed, mollitia lectus. Nulla vestibulum massa neque ut et, id hendrerit sit,
									feugiat in taciti enim proin nibh, tempor dignissim, rhoncus duis vestibulum nunc mattis convallis.
									Orci aliquet, in lorem et velit maecenas luctus, wisi nulla at, mauris nam ut a, lorem et et elit eu.
									Sed dui facilisi, adipiscing mollis lacus congue integer, faucibus consectetuer eros amet sit sit,
									magna dolor posuere. Placeat et, ac occaecat rutrum ante ut fusce. Sit velit sit porttitor non enim purus,
									id semper consectetuer justo enim, nulla etiam quis justo condimentum vel, malesuada ligula arcu. Nisl neque,
									ligula cras suscipit nunc eget, et tellus in varius urna odio est. Fuga urna dis metus euismod laoreet orci,
									litora luctus suspendisse sed id luctus ut. Pede volutpat quam vitae, ut ornare wisi. Velit dis tincidunt,
									pede vel eleifend nec curabitur dui pellentesque, volutpat taciti aliquet vivamus viverra, eget tellus ut
									feugiat lacinia mauris sed, lacinia et felis.'
			));
}
?>