<?php 
/* SVN FILE: $Id$ */
/* Processor Test cases generated on: 2008-07-30 17:07:23 : 1217463023*/
App::import('Model', 'Processor');

class TestProcessor extends Processor {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class ProcessorTestCase extends CakeTestCase {
	var $Processor = null;
	var $fixtures = array('app.processor');

	function start() {
		parent::start();
		$this->Processor = new TestProcessor();
	}

	function testProcessorInstance() {
		$this->assertTrue(is_a($this->Processor, 'Processor'));
	}

	function testProcessorFind() {
		$results = $this->Processor->recursive = -1;
		$results = $this->Processor->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Processor' => array(
			'id'  => 1,
			'name'  => 'Lorem ipsum dolor sit amet',
			'startdatetime'  => '2008-07-30 17:10:23',
			'lastseendatetime'  => '2008-07-30 17:10:23'
			));
		$this->assertEqual($results, $expected);
	}
}
?>