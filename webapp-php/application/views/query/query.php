<?php slot::start('head') ?>
    <title>Query Results - Mozilla Crash Reports</title>
    <?php echo html::stylesheet(array(
        'css/jquery.tooltip.css',
        'css/flora/flora.tablesorter.css',
    ),  'screen'); ?>
    
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.ui.all.js',       /* ui.accordion.js */
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',       /* old school not ui.sortable.js */
        'js/jquery/plugins/jquery.dimensions.min.js',
        'js/jquery/plugins/jquery.tooltip.min.js',
        'js/socorro/query.js',
        'js/socorro/bugzilla.js'
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

    <div class="page-heading">
        <h2>Query Results</h2>
    </div>

    <div class="panel">
        <div class="body notitle">

    <?php 
        View::factory('common/prose_params', array(
            'params'    => $params,
            'platforms' => $all_platforms
        ))->render(TRUE);
        
        View::factory('moz_pagination/nav')->render(TRUE);
        
        View::factory('common/list_by_signature', array(
            'items_per_page' => $items_per_page,
            'page'      => $page,
            'params'    => $params,
            'platforms' => $all_platforms,
            'reports'   => $reports,
            'sig2bugs'  => $sig2bugs
        ))->render(TRUE); 

    endif ?>
            <br />
        </div>
    </div>
