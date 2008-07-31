<?php 
/* SVN FILE: $Id$ */
/* Priorityjob Test cases generated on: 2008-07-30 17:07:21 : 1217463081*/
App::import('Model', 'Priorityjob');

class TestPriorityjob extends Priorityjob {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class PriorityjobTestCase extends CakeTestCase {
	var $Priorityjob = null;
	var $fixtures = array('app.priorityjob');

	function start() {
		parent::start();
		$this->Priorityjob = new TestPriorityjob();
	}

	function testPriorityjobInstance() {
		$this->assertTrue(is_a($this->Priorityjob, 'Priorityjob'));
	}

	function testPriorityjobFind() {
		$results = $this->Priorityjob->recursive = -1;
		$results = $this->Priorityjob->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Priorityjob' => array(
			'uuid'  => 'Lorem ipsum dolor sit amet'
			));
		$this->assertEqual($results, $expected);
	}
}
?>