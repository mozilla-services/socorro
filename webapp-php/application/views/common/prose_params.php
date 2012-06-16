<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * TODO: Better processing of the fields toward the bottom.
 */
?>
<p>
    <?php
        if ($params['date'] == '' || $params['date'] == date('Y-m-d', time())) {
            $end_date = "now";
        } else {
            $end_date = $params['date'];
        }

        $msg = "Results within {$params['range_value']} {$params['range_unit']} of {$end_date}";

        if ($params['query']) {

            $types = (array(
                'exact'      => 'is exactly',
                'contains'   => 'contains',
                'startswith' => 'starts with',
                'simple'     => 'contains'
            ));
            // default to simple
            $type = 'contains';
            if (in_array($params['query_type'], $types)) {
                $type = $types[ $params['query_type'] ];
            }

            $queries = (array(
                'signature' => 'the crash signature',
            ));
            // default to signature
            $query = 'the crash signature';
            if (in_array($params['query_search'], $queries)) {
                $query = $queries[ $params['query_search'] ];
            }

            $msg .= ", where {$query} {$type} '{$params['query']}'";

        }

        foreach (array('product', 'branch', 'version', 'platform') as $field) {
            if (count( $params[$field] )) {
                $msg .= ", and the $field is one of " . ucwords(join(', ', $params[$field]));
            }
        }

        if (array_key_exists('build_id', $params) &&
            ! empty($params['build_id'])) {
            $msg .= " for build " . $params['build_id'];
        }

        if (array_key_exists('process_type', $params) &&
            'all' != $params['process_type']) {
            if ('any' == $params['process_type']) {
                $msg .= " and the crashing process was of any type (including unofficial release channels)";
            } else {
                $msg .= " and the crashing process was a " . $params['process_type'];
                if ('plugin' == $params['process_type'] && trim($params['plugin_query']) != '') {
                    $plugin_copy = array('exact'  => ' that is exactly ',
                                         'contains' => ' that contains ',
                                         'startswith' => ' that starts with ',
                                        );
                    // default to contains
                    $plugin_query_type = 'that contains';
                    if (in_array($params['plugin_query_type'], $plugin_copy)) {
                        $plugin_query_type = $plugin_copy[ $params['plugin_query_type'] ];
                    }
                    $msg .= " " . $params['plugin_field'] . $plugin_query_type . $params['plugin_query'];
                }
            }
        }


        $msg .= '.';

        out::H($msg);
    ?>
</p>
