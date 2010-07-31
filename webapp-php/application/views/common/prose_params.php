<?php
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
                'startswith' => 'starts with'
            ));
            $type = $types[ $params['query_type'] ];

            $queries = (array( 
                'signature' => 'the crash signature',
                'stack'     => 'one of the top 10 stack frames'
            ));
            $query = $queries[ $params['query_search'] ];
        
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
	    $msg .= " and the crashing process was " . $params['process_type'];
	    if ('plugin' == $params['process_type'] && trim($params['plugin_query']) != '') {
		$plugin_copy = array('exact'  => ' that is exactly ',
				     'contains' => ' that contains ',
				     'startswith' => ' that starts with ',
		);
		$msg .= " " . $params['plugin_field'] . $plugin_copy[$params['plugin_query_type']] . $params['plugin_query'];
	    }
	}


        $msg .= '.';
        
        out::H($msg);
    ?>
</p>
