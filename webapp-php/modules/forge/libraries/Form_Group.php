<?php defined('SYSPATH') or die('No direct script access.');
/**
 * FORGE group library.
 *
 * $Id: Form_Group.php 2539 2008-04-20 17:44:55Z PugFish $
 *
 * @package    Forge
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Form_Group_Core extends Forge {

	protected $data = array
	(
		'type'  => 'group',
		'name'  => '',
		'class' => 'group',
		'label' => '',
		'message' => ''
	);

	// Input method
	public $method;

	public function __construct($name = NULL, $class = 'group')
	{
		$this->data['name'] = $name;
		$this->data['class'] = $class;

		// Set dummy data so we don't get errors
		$this->attr['action'] = '';
		$this->attr['method'] = 'post';
	}

	public function __get($key)
	{
		if ($key == 'type' || $key == 'name')
		{
			return $this->data[$key];
		}
		return parent::__get($key);
	}

	public function __set($key, $val)
	{
		if ($key == 'method')
		{
			$this->attr['method'] = $val;
		}
		$this->$key = $val;
	}

	public function label($val = NULL)
	{
		if ($val === NULL)
		{
			if ($label = $this->data['label'])
			{
				return $this->data['label'];
			}
		}
		else
		{
			$this->data['label'] = ($val === TRUE) ? ucwords(inflector::humanize($this->data['name'])) : $val;
			return $this;
		}
	}

	public function message($val = NULL)
	{
		if ($val === NULL)
		{
			return $this->data['message'];
		}
		else
		{
			$this->data['message'] = $val;
			return $this;
		}
	}

	public function render()
	{
		// No Sir, we don't want any html today thank you
		return;
	}

} // End Form Group