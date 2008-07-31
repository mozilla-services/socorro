<?php 
/* SVN FILE: $Id$ */
/* Branch Test cases generated on: 2008-07-30 17:07:21 : 1217462961*/
App::import('Model', 'Branch');

class TestBranch extends Branch {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class BranchTestCase extends CakeTestCase {
	var $Branch = null;
	var $fixtures = array('app.branch');

	function start() {
		parent::start();
		$this->Branch = new TestBranch();
	}

	function testBranchInstance() {
		$this->assertTrue(is_a($this->Branch, 'Branch'));
	}

	function testBranchFind() {
		$results = $this->Branch->recursive = -1;
		$results = $this->Branch->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Branch' => array(
			'product'  => 'Lorem ipsum dolor sit amet',
			'version'  => 'Lorem ipsum do',
			'branch'  => 'Lorem ipsum dolor sit '
			));
		$this->assertEqual($results, $expected);
	}
}
?>