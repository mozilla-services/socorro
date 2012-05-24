<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Responsible for knowing difference between types of releases.
 * If a version number contains 'pre' it is a development release.
 * Example: Firefox 3.6pre
 * If a version number contains 'a' or 'b' it is a milestone release.
 * Example: Firefox 3.5b99 - beta milestone release
 * Otherwise a version is considered a major build
 * Example: Firefox 3.0.12 or 3.5
 */
class Release
{
    //TODO pull in 'development' 'major' 'minor' strings from app into
    //const on this class
    const DEVELOPMENT = 'development';
    const MILESTONE = 'milestone';
    const MAJOR = 'major';

    public function typeOfRelease($version)
    {
        if (strpos($version, 'pre') !== false) {
  	    return self::DEVELOPMENT;
	} elseif (
            strpos($version, 'b') !== false ||
            strpos($version, 'a') !== false ||
            strpos($version, 'p') !== false
        ) {
  	    return self::MILESTONE;
        } else {
  	    return self::MAJOR;
	}
    }
}
?>
