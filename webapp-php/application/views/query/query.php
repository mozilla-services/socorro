<?php slot::start('head') ?>
    <title>Query Results - Mozilla Crash Reports</title>
    <?php echo html::stylesheet(array(
        'css/datePicker.css',
        'css/flora/flora.tablesorter.css',
	'css/jquery-ui-1.7.2/smoothness.custom.css' /* jquery ui 1.7.2 */
    ), 'screen')?>

    <?php echo html::script(array(
				  //'js/jquery/plugins/ui/jquery.ui.all.js',       /* ui.accordion.js */
        'js/jquery/plugins/ui/jquery-ui-1.7.2.custom.min.js',       /* ui.accordion.js jquery ui 1.7.2 */
        'js/jquery/date.js',
        'js/jquery/plugins/ui/jquery.datePicker.js',     /* old school not ui.datepicker.js */
	        'js/jquery/plugins/ui/jquery.tablesorter.min.js',       /* old school not ui.sortable.js */
        'js/socorro/query.js'
    ))?>

    <script type="text/javascript">
    var socSearchFormModel = <?php echo json_encode($params) ?>;
    </script>
<?php slot::end(); 

     View::factory('common/query_form', array(
        'searchFormModel'    => $params,
        'versions_by_product' => $versions_by_product
     ))->render(TRUE);

    if ($params['do_query'] !== FALSE): ?>
    <h2 id="query-results-h">Query Results</h2>

    <?php 
        View::factory('common/prose_params', array(
            'params'    => $params,
            'platforms' => $all_platforms
        ))->render(TRUE);

        View::factory('common/list_by_signature', array(
            'params'    => $params,
            'platforms' => $all_platforms,
            'reports'   => $reports,
	    'sig2bugs'   => $sig2bugs
	))->render(TRUE); 


    endif ?>
