<?php
// ***** BEGIN LICENSE BLOCK *****
// Version: MPL 1.1/GPL 2.0/LGPL 2.1
//
// The contents of this file are subject to the Mozilla Public License Version
// 1.1 (the "License"); you may not use this file except in compliance with
// the License. You may obtain a copy of the License at
// http://www.mozilla.org/MPL/
//
// Software distributed under the License is distributed on an "AS IS" basis,
// WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
// for the specific language governing rights and limitations under the
// License.
//
// The Original Code is Mozilla Update.
//
// Contributor(s):
//        Benjamin Smedberg
//        Mike Morgan
//        Justin Scott
//        Mike Shaver
//
// Alternatively, the contents of this file may be used under the terms of
// either the GNU General Public License Version 2 or later (the "GPL"), or
// the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
// in which case the provisions of the GPL or the LGPL are applicable instead
// of those above. If you wish to allow use of your version of this file only
// under the terms of either the GPL or the LGPL, and not to allow others to
// use your version of this file under the terms of the MPL, indicate your
// decision by deleting the provisions above and replace them with the notice
// and other provisions required by the GPL or the LGPL. If you do not delete
// the provisions above, a recipient may use your version of this file under
// the terms of any one of the MPL, the GPL or the LGPL.
//
// ***** END LICENSE BLOCK *****

/**
 * Version comparison script.  The purpose of this file is to mimic the C++
 * version comparison algorithm so version comparisons in VersionCheck.php are
 * properly executed with expected results.  This could have been accomplished
 * by establishing a standardized versioning scheme across all Mozilla
 * operations, but although that would make more sense, it's simply too late
 * for that now.  We cannot escape this.
 *
 * @package umo
 * @subpackage core
 */

define('COMPAT_LATEST', 'latest');
define('COMPAT_BETA', 'beta');
define('COMPAT_ALPHA', 'alpha');
define('COMPAT_OTHER', 'other');

class VersioncompareComponent /* extends Object */ {
    /**
     * Parse a version part.
     * @return array $r parsed version part.
     */
    function parseVersionPart($p) {
        if ($p == '*') {
            return array('numA'   => 2147483647,
                         'strB'   => '',
                         'numC'   => 0,
                         'extraD' => '');
        }

        preg_match('/^([-\d]*)([^-\d]*)([-\d]*)(.*)$/', $p, $m);

        $r = array('numA'   => intval($m[1]),
                   'strB'   => $m[2],
                   'numC'   => intval($m[3]),
                   'extraD' => $m[4]);

        if ($r['strB'] == '+') {
            ++$r['numA'];
            $r['strB'] = 'pre';
        }

        return $r;
    }

    /**
     * Compare parsed version parts.
     * @param string $an
     * @param string $bp
     * @return int $r
     */
    function cmp($an, $bn) {
        if ($an < $bn)
            return -1;

        if ($an > $bn)
            return 1;

        return 0;
    }

    /**
     * Recursive string comparison.
     * @param string $as
     * @param string $bs
     * @return int $r
     */
    function strcmp($as, $bs) {
        if ($as == $bs)
            return 0;

        if ($as == '')
            return 1;

        if ($bs == '')
            return -1;

        return strcmp($as, $bs);
    }

    /**
     * Compare parsed version numbers.
     * @param string $ap
     * @param string $bp
     * @return int $r -1|0|1
     */
    function compareVersionParts($ap, $bp) {
        $avp = $this->parseVersionPart($ap);
        $bvp = $this->parseVersionPart($bp);

        $r = $this->cmp($avp['numA'], $bvp['numA']);
        if ($r)
            return $r;

        $r = $this->strcmp($avp['strB'], $bvp['strB']);
        if ($r)
            return $r;

        $r = $this->cmp($avp['numC'], $bvp['numC']);
        if ($r)
            return $r;

        return $this->strcmp($avp['extraD'], $bvp['extraD']);
    }

    /**
     * Master comparison function.
     * @param string $a complete version string.
     * @param string $b complete version string.
     * @return int $r -1|0|1
     */
    function compareVersions($a, $b) {
        $al = explode('.', $a);
        $bl = explode('.', $b);

        while (count($al) || count($bl)) {
            $ap = array_shift($al);
            $bp = array_shift($bl);

            $r = $this->compareVersionParts($ap, $bp);
            if ($r != 0)
                return $r;
        }

        return 0;
    }

    /**
     * Is $test between $lower and $upper (inclusive)?
     * @param string $test complete version under test
     * @param string $lower complete version of lower bound
     * @param string $upper complete version of upper bound
     */
    function versionBetween($test, $lower, $upper) {
        if ($this->compareVersions($test, $lower) == -1) {
            return false;
        }

        if ($this->compareVersions($test, $upper) == 1) {
            return false;
        }

        return true;
    }

    /**
     * Sort a version array, using this version comparison component
     * @param Appversion model result array
     * @return bool success
     */
    function sortAppversionArray(&$a) {
        if (is_array(current($a))) {
            return uasort($a, array(&$this, '_compareCakeResultVersions'));
        }
        else {
            return uasort($a, array(&$this, 'compareVersions'));
        }
    }

    /**
     * Wrapper for compareVersions (respecting Cake's result arrays)
     */
    function _compareCakeResultVersions($a,$b) {
        return $this->CompareVersions($a['Appversion']['version'], $b['Appversion']['version']);
    }

    /**
     * Grades an array of appversions relative to their compatibility with a
     * major version.
     * @param string $compatibility_version major version, like 3.0 or 3.1
     * @param array $versions array of version strings to grade
     * @return array appversion => grade
     */
    function getCompatibilityGrades($compatibility_version, $versions) {
        $this->sortAppversionArray($versions);
        $versions = array_reverse($versions, true);

        $appversions = array();
        $highestFound = false;

        foreach ($versions as $version) {
            // If highest version hasn't been found but this is pre, count it anyway
            if (!$highestFound && strpos($version, 'pre') !== false) {
                $appversions[$version] = COMPAT_LATEST;
                continue;
            }
            // This version is the highest without pre, so mark highest as found
            if (!$highestFound) {
                $appversions[$version] = COMPAT_LATEST;
                $highestFound = true;
                continue;
            }
            if (strpos($version, 'b') !== false) {
                $appversions[$version] = COMPAT_BETA;
                continue;
            }
            if (strpos($version, 'a') !== false) {
                $appversions[$version] = COMPAT_ALPHA;
                continue;
            }
            // Release candidates and final (3.1, 3.1pre, 3.1rc1) are colored as beta
            if (strpos($version, 'rc') !== false || $version == $compatibility_version || $version == "{$compatibility_version}pre") {
                $appversions[$version] = COMPAT_BETA;
                continue;
            }

            $appversions[$version] = COMPAT_OTHER;
        }

        return $appversions;
    }

    /**
     * Grades an appversion relative to a major version.
     * @param string $version the version to grade
     * @param string $compatibility_version the major version
     * @param array $gradedArray array of existing grades, output from getCompatibilityGrades()
     * @return string compatibility grade constant
     */
    function gradeCompatibility($version, $compatibility_version, $gradedArray) {
        // See if maxversion is identified as related to this major version
        if (array_key_exists($version, $gradedArray))
            return $gradedArray[$version];
        elseif ($this->compareVersions($version, $compatibility_version) > 0)
            return COMPAT_LATEST;
        else
            return COMPAT_OTHER;
    }

    /**
     * Returns an array of version strings corresponding to the $aliases map
     * $version => (x, y)
     */
    function _versionAlias($version, $aliases) {
        // Just return the version if there aren't any aliases.
        if (!array_key_exists($version, $aliases)) {
            return array($version);
        }
        else {
            $alias = $aliases[$version];
            // Make sure $version is in the returned array.
            if (!in_array($version, $alias)) {
                array_push($alias, $version);
            }
            return $alias;
        }
    }
}
?>
