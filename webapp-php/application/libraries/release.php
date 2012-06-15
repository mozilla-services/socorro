<?php defined('SYSPATH') or die('No direct script access.');
/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Socorro Crash Reporter
 *
 * The Initial Developer of the Original Code is
 * The Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Austin King <aking@mozilla.com> (Original Author)
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

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
