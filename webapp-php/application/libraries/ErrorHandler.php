<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Mainly this provides an error handler and error detection
 * mechanism.
 */
class ErrorHandler
{
    public $error_reading_file = FALSE;

    /**
     * Handles errors fetching Correlation reports
     * Callers must reset $this->error_reading_file to FALSE
     * before use and then check it after IO calls.
     * @see set_error_handler
     */
    public function handleError($errno, $errstr, $errfile, $errline)
    {
        $severity = 'error';
        if (strstr($errstr, 'HTTP/1.1 404 Not Found')) {
            $severity = 'alert';
        }

        Kohana::log($severity, "$errstr $errfile line $errline");
        $this->error_reading_file = TRUE;
    }
}
?>
