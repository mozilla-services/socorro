<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Helpers to capture and include named slots for templates.
 */
class slot_Core
{

    // Stack of current named open capture slots
    public static $slot_stack = array();

    // Array of named captured slots
    public static $slots = array();

    // Current controller wanting copies of slot
    public static $controller = FALSE;

    /**
     * Start capturing output for the given named slot.
     *
     * @param string name of the slot to capture
     */
    public static function start($key)
    {
        array_push(self::$slot_stack, $key);
        ob_start();
    }

    /**
     * Finish capturing output for current opened slot.
     *
     * @return string
     */
    public static function end()
    {
        $key = array_pop(self::$slot_stack);
        if ($key == NULL) {
            return FALSE;
        } else {
            $output = ob_get_contents();
            ob_end_clean();
            self::set($key, $output);
            return $key;
        }
    }

    /**
     * Set the current controller for setting view data
     *
     * @param object the current controller.
     */
    public static function setController($controller=FALSE)
    {
        self::$controller = $controller;
    }

    /**
     * Set content for a named slot, optionally updating the controller.
     *
     * @param string name of the slot
     * @param string content for the slot
     */
    public static function set($name, $value)
    {
        self::$slots[$name] = $value;
        if (self::$controller)
            self::$controller->setViewData($name, $value);
    }

    /**
     * Get one or all stored slots.
     *
     * @param  string name of the slot to return, or omit to fetch all
     * @return string|array
     */
    public static function get($name=FALSE, $default='')
    {
        if ($name) {
            return isset(self::$slots[$name]) ?
                trim(self::$slots[$name]) : $default;
        } else {
            return self::$slots;
        }
    }

    /**
     * Determine whether a particular slot has been created.
     *
     * @return boolean
     */
    public static function exists($name=FALSE)
    {
        return array_key_exists($name, self::$slots);
    }

    /**
     * Output the contents of a named slot
     *
     * @param string name of the desired slot.
     */
    public static function output($name=FALSE, $default='')
    {
        echo self::get($name, $default);
    }

}
