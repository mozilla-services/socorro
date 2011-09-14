<?php
/**
 * Helper for setting cache control headers - currently etag, last-modified,
 * and expires
 */
class cachecontrol_Core
{
    /**
     * Set cache control headers
     *
     * @param array Options for headers - etag, last_modified, expires.
     */
    public static function set($opts) {

        // Accept strings, arrays, or objects for Etag.
        if (isset($opts['etag'])) {
            $etag = $opts['etag'];

            if (is_array($etag)) {

                // Ignore order of the keys in the etag array by sorting.
                $names = array_keys($etag);
                sort($names);

                // Assemble the keys and values into a string and MD5 it.
                $parts = array();
                foreach($names as $name) {
                    $parts[] = $name . '=' . $etag[$name];
                }
                $etag = md5( join('&', $parts) );

            } else if (is_object($etag)) {
                $etag = md5(var_export($etag, true));
            } else {
                $etag = md5("$etag");
            }

            header("Etag: $etag");
        }

        // Accept date string or time in seconds for Last-Modified.
        if (isset($opts['last-modified'])) {
            $lmod = $opts['last-modified'];
            if (is_numeric($lmod)) {
                $lmod = date('r', $lmod);
            }
            header("Last-Modified: $lmod");
        }

        // Accept date string or time in seconds for Expires.
        if (isset($opts['expires'])) {
            $expires = $opts['expires'];
            if (is_numeric($expires)) {
                $expires = date('r', $expires);
            }
            header("Expires: $expires");
        }

    }

}
