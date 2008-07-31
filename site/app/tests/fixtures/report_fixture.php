<?php 
/* SVN FILE: $Id$ */
/* Report Fixture generated on: 2008-07-30 17:07:59 : 1217463359*/

class ReportFixture extends CakeTestFixture {
	var $name = 'Report';
	var $table = 'reports';
	var $fields = array(
			'id' => array('type'=>'integer', 'null' => false, 'length' => 11, 'key' => 'primary'),
			'date' => array('type'=>'datetime', 'null' => false),
			'uuid' => array('type'=>'string', 'null' => false, 'length' => 50),
			'product' => array('type'=>'string', 'null' => true, 'length' => 30),
			'version' => array('type'=>'string', 'null' => true, 'length' => 16),
			'build' => array('type'=>'string', 'null' => true, 'length' => 30),
			'signature' => array('type'=>'string', 'null' => true),
			'url' => array('type'=>'string', 'null' => true),
			'install_age' => array('type'=>'integer', 'null' => true),
			'last_crash' => array('type'=>'integer', 'null' => true),
			'uptime' => array('type'=>'integer', 'null' => true),
			'comments' => array('type'=>'string', 'null' => true, 'length' => 500),
			'cpu_name' => array('type'=>'string', 'null' => true, 'length' => 100),
			'cpu_info' => array('type'=>'string', 'null' => true, 'length' => 100),
			'reason' => array('type'=>'string', 'null' => true),
			'address' => array('type'=>'string', 'null' => true, 'length' => 20),
			'os_name' => array('type'=>'string', 'null' => true, 'length' => 100),
			'os_version' => array('type'=>'string', 'null' => true, 'length' => 100),
			'email' => array('type'=>'string', 'null' => true, 'length' => 100),
			'build_date' => array('type'=>'datetime', 'null' => true),
			'user_id' => array('type'=>'string', 'null' => true, 'length' => 50),
			'date_processed' => array('type'=>'datetime', 'null' => false, 'default' => 'now()'),
			'starteddatetime' => array('type'=>'datetime', 'null' => true),
			'completeddatetime' => array('type'=>'datetime', 'null' => true),
			'success' => array('type'=>'boolean', 'null' => true),
			'message' => array('type'=>'text', 'null' => true, 'length' => 1073741824),
			'truncated' => array('type'=>'boolean', 'null' => true),
			'indexes' => array('0' => array())
			);
	var $records = array(array(
			'id'  => 1,
			'date'  => '2008-07-30 17:15:59',
			'uuid'  => 'Lorem ipsum dolor sit amet',
			'product'  => 'Lorem ipsum dolor sit amet',
			'version'  => 'Lorem ipsum do',
			'build'  => 'Lorem ipsum dolor sit amet',
			'signature'  => 'Lorem ipsum dolor sit amet',
			'url'  => 'Lorem ipsum dolor sit amet',
			'install_age'  => 1,
			'last_crash'  => 1,
			'uptime'  => 1,
			'comments'  => 'Lorem ipsum dolor sit amet',
			'cpu_name'  => 'Lorem ipsum dolor sit amet',
			'cpu_info'  => 'Lorem ipsum dolor sit amet',
			'reason'  => 'Lorem ipsum dolor sit amet',
			'address'  => 'Lorem ipsum dolor ',
			'os_name'  => 'Lorem ipsum dolor sit amet',
			'os_version'  => 'Lorem ipsum dolor sit amet',
			'email'  => 'Lorem ipsum dolor sit amet',
			'build_date'  => '2008-07-30 17:15:59',
			'user_id'  => 'Lorem ipsum dolor sit amet',
			'date_processed'  => '2008-07-30 17:15:59',
			'starteddatetime'  => '2008-07-30 17:15:59',
			'completeddatetime'  => '2008-07-30 17:15:59',
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
									feugiat lacinia mauris sed, lacinia et felis.',
			'truncated'  => 1
			));
}
?>