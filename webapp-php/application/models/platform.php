<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Row class for platform info
 */
class Platform {

    public function __construct($id, $name, $os_name, $color) {
        $this->id      = $id;
        $this->name    = $name;
        $this->os_name = $os_name;
        $this->color   = $color;
    }

}

/**
 * Common model class managing the set of platforms
 */
class Platform_Model extends Model {

    public static $platform_list;

    /**
     * Construct ths set of known platforms.
     */
    public function __construct() {
        parent::__construct();

        $platforms = array();
        foreach(array('win', 'mac', 'lin') as $os):
            $platforms[] = new Platform(
                    Kohana::config("platforms.${os}_id"),
            Kohana::config("platforms.${os}_name"),
            Kohana::config("platforms.${os}_os_name"),
            Kohana::config("platforms.${os}_color")
            );
        endforeach;

        $this->platform_list = array();
        foreach ($platforms as $platform) {
            $this->platform_list[$platform->id] = $platform;
        }

    }

    /**
     * Get a list of all known platforms.
     *
     * @return array List of platforms
     */
    public function getAll() {
        return array_values($this->platform_list);
    }

    /**
     * Fetch a platform by ID, if available.
     *
     * @param  string Platform ID
     * @return object The platform found, or FALSE
     */
    public function get($id) {
        return array_key_exists($id, $this->platform_list) ?
            $this->platform_list[$id] : FALSE;
    }

}
