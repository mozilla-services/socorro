<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Flot (jQuery plotting plugin) Kohana integration.
 *
 * $Id: Flot.php 1993 2008-02-08 18:05:46Z armen $
 *
 * @package    Flot
 * @author     Woody Gilk
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Flot_Core {

	// Container type and attributes
	protected $type = 'div';
	protected $attr = array();

	// Dataset and options
	protected $dataset;
	protected $options;

	public function __construct($id, $attr = array(), $type = NULL)
	{
		// Set the id to the attributes
		$attr['id'] = $id;

		// Set the attributes of the container
		$this->attr += $attr;

		// Set the type, if not NULL
		empty($type) or $this->type = $type;

		// Create the data set array
		$this->dataset = array();

		// Create the options object
		$this->options = new StdClass;
	}

	public function __get($key)
	{
		if ( ! isset($this->options->$key))
		{
			// Create the object if it does not exist
			$this->options->$key = new StdClass;
		}

		// Return the option
		return $this->options->$key;
	}

	public function __set($key, $value)
	{
		// Set the option value
		$this->options->$key = $value;
	}

	/**
	 * Return the rendered graph as an HTML string.
	 *
	 * @return string
	 */
	public function __toString()
	{
		return $this->render();
	}

	/**
	 * Add data to the data set.
	 *
	 * @chainable
	 * @param   object   a constructed Flot_Dataset
	 * @return  object
	 */
	public function add(Flot_Dataset $set, $label = NULL)
	{
		// Add the label, if requested
		empty($label) or $set->label = $label;

		// Add the set to the current data set
		$this->dataset[] = $set;

		return $this;
	}

	/**
	 * Set options.
	 *
	 * @chainable
	 * @param   string  option name
	 * @param   mixed   options value
	 * @return  object
	 */
	public function set($key, $value)
	{
		// Set the requested value
		$this->__set($key, $value);

		return $this;
	}

	/**
	 * Return the rendered graph as an HTML string.
	 *
	 * @return string
	 */
	public function render($template = 'kohana_flot')
	{
		// Load the template
		return View::factory($template)
			// Set container properties
			->set('type', $this->type)
			->set('attr', $this->attr)
			// JSON encode the dataset and options
			->set('dataset', array_map('json_encode', $this->dataset))
			->set('options', json_encode($this->options))
			// And return the rendered view
			->render();
	}

} // End Flot