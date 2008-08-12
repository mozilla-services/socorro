<?php slot::start('head') ?>
    <title>Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?> <?php out::H($build_id) ?></title>
    <?php echo html::script(array(
        'js/jquery/jquery-1.2.1.js',
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
    ))->render(TRUE) 
?>
