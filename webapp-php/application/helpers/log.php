<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Log helper that combines usage of both FirePHP and Kohana native logging.
 */
require('FirePHPCore/FirePHP.class.php');
class log_Core
{

    public static function info($msg) {
        return self::log($msg, FirePHP::INFO);
    }

    public static function debug($msg) {
        return self::log($msg, FirePHP::LOG);
    }

    public static function warn($msg) {
        return self::log($msg, FirePHP::WARN);
    }

    public static function error($msg) {
        return self::log($msg, FirePHP::ERROR);
    }

    /**
     * Emit a log message to both FirePHP and Kohana, following FirePHP
     * variable parameters style:
     *
     * log::log( mixed $Object [, string $Label ] [, string $Type ] )
     */
    public static function log($Object) {

        $firephp = FirePHP::getInstance(true);

        $fb_to_kohana_types = array(
            FirePHP::LOG       => 'debug',
            FirePHP::INFO      => 'info',
            FirePHP::WARN      => 'alert',
            FirePHP::ERROR     => 'error',
            FirePHP::DUMP      => 'debug',
            FirePHP::TRACE     => 'debug',
            FirePHP::EXCEPTION => 'debug',
            FirePHP::TABLE     => 'debug'
        );

        $args = func_get_args();

        if (count($args) == 1) {

            $firephp->fb($Object);
            Kohana::log('info', $Object);

        } else if(count($args) == 2) {

            if (array_key_exists($args[1], $fb_to_kohana_types)) {
                $level = $fb_to_kohana_types[$args[1]];
                $msg = $Object;
            } else {
                $level = 'debug';
                $msg = $args[1] . ": " . var_export($Object, true);
            }

            $firephp->fb($Object, $args[1]);
            Kohana::log($level, $msg);

        } else if(count($args)==3) {

            $level = (array_key_exists($args[2], $fb_to_kohana_types)) ?
                $fb_to_kohana_types[$args[2]] : 'info';
            $msg = $args[1] . ": " . var_export($Object, true);

            $firephp->fb($Object, $args[1], $args[2]);
            Kohana::log($level, $msg);

        }

    }

}
