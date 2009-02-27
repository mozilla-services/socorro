<?php slot::start('head') ?>
    <title>Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?> <?php out::H($build_id) ?></title>
    <link title="CSV formatted Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?> <?php out::H($build_id) ?>" 
          type="text/csv" rel="alternate" href="?format=csv" />
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.tablesorter.min.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>

    <script type="text/javascript">
    $(document).ready(function() { 
      $("#signatureList").tablesorter(); 
    }); 
    </script>
<?php slot::end() ?>

<h1 class="first">Top Crashers for <?php out::H($product) ?> <?php out::H($version) ?> <?php out::H($build_id) ?></h1>

<?php 
    View::factory('common/list_topcrashers', array(
        'last_updated' => $last_updated,
        'top_crashers' => $top_crashers
    ))->render(TRUE);
    if (count($top_crashers) > 0) {
        View::factory('common/csv_link_copy')->render(TRUE);
    }
?>
