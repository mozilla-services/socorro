<?php
/**
 * Initialization hook for Recaptcha module.
 *
 * @package Recaptcha
 */
class Recaptcha_Init
{
    public static function init()
    {
        include_once(Kohana::find_file('vendor', 'recaptchalib'));
    }
}
Recaptcha_Init::init();
