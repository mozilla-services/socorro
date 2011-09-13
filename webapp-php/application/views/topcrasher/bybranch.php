<?php slot::start('head') ?>
    <title>Top Crashers for the <?php out::H($branch) ?> Branch</title>
    <link title="CSV formatted Top Crashers for the <?php out::H($branch) ?> Branch" type="text/csv" rel="alternate" href="?format=csv" />
    <?php echo html::script(array(
      'js/jquery/plugins/ui/jquery.tablesorter.min.js',
      'js/socorro/topcrash.js',
       'js/socorro/bugzilla.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>
    <script type="text/javascript">
        $(document).ready(function() {
              $('#signatureList').tablesorter();
        } );
    </script>
<?php slot::end() ?>

<h1 class="first">Top Crashers for the <span class="current-branch"><?php out::H($branch) ?></span> Branch</h1>
<?php
    View::factory('common/list_topcrashers_old', array(
		      'last_updated' => $last_updated,
		      'top_crashers' => $top_crashers
		      ))->render(TRUE);
?>
