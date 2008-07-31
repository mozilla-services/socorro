<?php 
/* SVN FILE: $Id$ */
/* Job Test cases generated on: 2008-07-30 17:07:14 : 1217463434*/
App::import('Model', 'Job');

class TestJob extends Job {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class JobTestCase extends CakeTestCase {
	var $Job = null;
	var $fixtures = array('app.job');

	function start() {
		parent::start();
		$this->Job = new TestJob();
	}

	function testJobInstance() {
		$this->assertTrue(is_a($this->Job, 'Job'));
	}

	function testJobFind() {
		$results = $this->Job->recursive = -1;
		$results = $this->Job->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Job' => array(
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
		$this->assertEqual($results, $expected);
	}
}
?>