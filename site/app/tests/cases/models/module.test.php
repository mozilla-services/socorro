<?php 
/* SVN FILE: $Id$ */
/* Module Test cases generated on: 2008-07-30 17:07:41 : 1217463161*/
App::import('Model', 'Module');

class TestModule extends Module {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class ModuleTestCase extends CakeTestCase {
	var $Module = null;
	var $fixtures = array('app.module');

	function start() {
		parent::start();
		$this->Module = new TestModule();
	}

	function testModuleInstance() {
		$this->assertTrue(is_a($this->Module, 'Module'));
	}

	function testModuleFind() {
		$results = $this->Module->recursive = -1;
		$results = $this->Module->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Module' => array(
			'report_id'  => 1,
			'module_key'  => 1,
			'filename'  => 'Lorem ipsum dolor sit amet',
			'debug_id'  => 'Lorem ipsum dolor sit amet',
			'module_version'  => 'Lorem ipsum d',
			'debug_filename'  => 'Lorem ipsum dolor sit amet'
			));
		$this->assertEqual($results, $expected);
	}
}
?>