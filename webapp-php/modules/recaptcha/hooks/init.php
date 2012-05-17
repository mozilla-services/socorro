/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
