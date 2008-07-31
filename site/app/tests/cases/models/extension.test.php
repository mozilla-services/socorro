<?php 
/* SVN FILE: $Id$ */
/* Extension Test cases generated on: 2008-07-30 17:07:53 : 1217463173*/
App::import('Model', 'Extension');

class TestExtension extends Extension {
	var $cacheSources = false;
	var $useDbConfig  = 'test_suite';
}

class ExtensionTestCase extends CakeTestCase {
	var $Extension = null;
	var $fixtures = array('app.extension');

	function start() {
		parent::start();
		$this->Extension = new TestExtension();
	}

	function testExtensionInstance() {
		$this->assertTrue(is_a($this->Extension, 'Extension'));
	}

	function testExtensionFind() {
		$results = $this->Extension->recursive = -1;
		$results = $this->Extension->find('first');
		$this->assertTrue(!empty($results));

		$expected = array('Extension' => array(
			'report_id'  => 1,
			'extension_key'  => 1,
			'extension_id'  => 'Lorem ipsum dolor sit amet',
			'extension_version'  => 'Lorem ipsum do'
			));
		$this->assertEqual($results, $expected);
	}
}
?>