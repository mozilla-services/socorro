<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Outputs the dynamic Captcha resource.
 * Usage: Call the Captcha controller from a view, e.g.
 *        <img src="<?php echo url::site('captcha') ?>" />
 *
 * $Id: captcha.php 3281 2008-08-06 16:13:58Z Shadowhand $
 *
 * @package    Captcha
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Captcha_Controller extends Controller {

	public function __call($method, $args)
	{
		// Output the Captcha challenge resource (no html)
		// Pull the config group name from the URL
		Captcha::factory($this->uri->segment(2))->render(FALSE);
	}

} // End Captcha_Controller
