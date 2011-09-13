<?php defined('SYSPATH') or die('No direct script access.');
/**
 * FORGE radio input library.
 *
 * $Id: Form_Radio.php 3039 2008-07-10 19:56:12Z Shadowhand $
 *
 * @package    Forge
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Form_Radio_Core extends Form_Checkbox {

	protected $data = array
	(
		'type' => 'radio',
		'class' => 'radio',
		'value' => '1',
		'checked' => FALSE,
	);

} // End Form_Radio
