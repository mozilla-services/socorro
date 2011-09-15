<?php defined('SYSPATH') or die('No direct script access.');
/**
 * FORGE checkbox input library.
 *
 * $Id: Form_Checkbox.php 3039 2008-07-10 19:56:12Z Shadowhand $
 *
 * @package    Forge
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Form_Checkbox_Core extends Form_Input {

	protected $data = array
	(
		'type' => 'checkbox',
		'class' => 'checkbox',
		'value' => '1',
		'checked' => FALSE,
	);

	protected $protect = array('type');

	public function __get($key)
	{
		if ($key == 'value')
		{
			// Return the value if the checkbox is checked
			return $this->data['checked'] ? $this->data['value'] : NULL;
		}

		return parent::__get($key);
	}

	public function label($val = NULL)
	{
		if ($val === NULL)
		{
			// Do not display labels for checkboxes, labels wrap checkboxes
			return '';
		}
		else
		{
			$this->data['label'] = ($val === TRUE) ? utf8::ucwords(inflector::humanize($this->name)) : $val;
			return $this;
		}
	}

	protected function html_element()
	{
		// Import the data
		$data = $this->data;

		if (empty($data['checked']))
		{
			// Not checked
			unset($data['checked']);
		}
		else
		{
			// Is checked
			$data['checked'] = 'checked';
		}

		if ($label = arr::remove('label', $data))
		{
			// There must be one space before the text
			$label = ' '.ltrim($label);
		}

		return '<label>'.form::input($data).$label.'</label>';
	}

	protected function load_value()
	{
		if (is_bool($this->valid))
			return;

		// Makes the box checked if the value from POST is the same as the current value
		$this->data['checked'] = ($this->input_value($this->name) == $this->data['value']);
	}

} // End Form Checkbox
