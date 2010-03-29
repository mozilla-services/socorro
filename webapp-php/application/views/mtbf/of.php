<?php slot::start('head') ?>
    <title><?php echo $title ?></title>
    <link title="CSV formatted <?php echo $title ?>" type="text/csv" rel="alternate" href="?format=csv" />

    <?php echo html::stylesheet(array(
       'css/flora/flora.all.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.5/excanvas.pack.js') ?><![endif]-->
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.5/jquery.flot.pack.js',
        'js/socorro/mtbf.js'
    ))?>
<?php slot::end() ?>
<?php 
  if( isset($error_message)){
?>
  <h1>Error</h1>
  <p class="error notice"><?php echo $error_message ?></p>
<?php
  }else{

   ?>

<div class="page-heading">
    <h2>Mean Time Before Failure - <span id="mtbf-product"><?php echo $product . "</span> <span id='mtbf-release-level'>" . $release_level ?></span></h2>
    <ul class="options">
        <li><a href="major" class="<?php if ($release_level == 'major') echo 'selected'; ?>">Major</a></li>
        <li><a href="milestone" class="<?php if ($release_level == 'milestone') echo 'selected'; ?>">Milestone</a></li>
        <li><a href="development" class="<?php if ($release_level == 'development') echo 'selected'; ?>">Development</a></li>
	</ul>
</div>


<div class="panel">
    <div class="title">Average number of seconds before a crash. Day 0 of release through day 60.</div>
    <div class="body">
        
<?php
    if( count($releases) ==0 ){
?>
<p class="message">No data is currently available for <?php echo $product . " " . $release_level; ?> releases.</p>
<?php    
    } else {
?>

<div id="overviewLegend"></div>

<div id="mtbf-graph"></div>

<a id="mtbf-os-drilldown" href="#">Drill down on OS</a><?php 
  echo html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17' ),
	            array('class' => 'ajax-loading', 'style' => 'display:none', 'alt' => 'More content loading')); ?>
<ul id="mtbf-data-details">
  <li>Data Loading</li>
</ul>

<script type="text/javascript">
var SocMtbfSeries = <?php echo json_encode( $releases ); ?>;
</script>
<?php 
    View::factory('common/csv_link_copy')->render(TRUE);

    } //if/else no data
} //if/else error message for url
 ?>


    </div>
</div>



