<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Captcha driver for "word" style.
 *
 * $Id: Word.php 3028 2008-07-10 13:33:05Z Geert $
 *
 * @package    Captcha
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Captcha_Word_Driver extends Captcha_Basic_Driver {

	/**
	 * Generates a new Captcha challenge.
	 *
	 * @return  string  the challenge answer
	 */
	public function generate_challenge()
	{
		// Load words from the current language and randomize them
		$words = Kohana::lang('captcha.words');
		shuffle($words);

		// Loop over each word...
		foreach ($words as $word)
		{
			// ...until we find one of the desired length
			if (abs(Captcha::$config['complexity'] - strlen($word)) < 2)
				return strtoupper($word);
		}

		// Return any random word as final fallback
		return strtoupper($words[array_rand($words)]);
	}

} // End Captcha Word Driver Class
