<?php
/**
 * TODO: Better processing of the fields toward the bottom.
 */
?>
<p>
    <?php
      if( isset($queryTooBroad) && $queryTooBroad ){
    ?>
  <strong>Warning:</strong> Your search was not specific enough. Please note we actually searched for:<br />
    <?php
       }

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
                $msg .= ", and the $field is one of " . join(', ', $params[$field]);
            }
        }

        $msg .= '.';
        
        out::H($msg);
    ?>
</p>
