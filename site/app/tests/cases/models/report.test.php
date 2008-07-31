<?php 
/* SVN FILE: $Id$ */
/* Report Test cases generated on: 2008-07-30 17:07:59 : 1217463359*/
App::import('Model', 'Report');

class TestReport extends Report {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class ReportTestCase extends CakeTestCase {
	var $Report = null;
	var $fixtures = array('app.report');

	function start() {
		parent::start();
		$this->Report = new TestReport();
	}

	function testReportInstance() {
		$this->assertTrue(is_a($this->Report, 'Report'));
	}

	function testReportFind() {
		$results = $this->Report->recursive = -1;
		$results = $this->Report->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Report' => array(
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
		$this->assertEqual($results, $expected);
	}
}
?>