<?php slot::start('head') ?>
    <title><?php echo $title ?></title>
    <?php echo html::stylesheet(array(
       'css/flora/flora.all.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.5/excanvas.pack.js') ?><![endif]-->
    <?php echo html::script(array(
        'js/jquery/jquery-1.2.1.js',
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
<h1 class="first">Mean Time Before Failure</h1>
<h2 class="mtbf-graph"><span id="mtbf-product"><?php echo $product . "</span> <span id='mtbf-release-level'>" . $release_level ?></span> releases</h2>
      <?php echo Kohana::debug() ?>
<div class="mtbf-nav-panel">
  <ul>Release type: 
      <li><a href="major" class="nav <?php     if($release_level == 'major'){?> current<?php } ?>">Major</a><li>
    <li><a href="milestone" class="nav <?php   if($release_level == 'milestone'){?> current<?php } ?>">Milestone</a><li>
    <li><a href="development" class="nav <?php if($release_level == 'development'){?> current<?php } ?>">Development</a><li>
  </ul>
</div>

<?php
    if( count($releases) ==0 ){
?>
<p class="message">No data is currently availabe for <?php echo $product . " " . $release_level; ?> releases.</p>
<?php    
    } else {
?>

<div id="overviewLegend"></div>

<div id="mtbf-graph"></div>
<div class="caption plot-label">Average number of seconds before a crash. Day 0 of release through day 60.</div>

<table id="firefox3.0.3-legend"></table>

<a id="mtbf-os-drilldown" href="#">Drill down on OS</a><?php 
  echo html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17' ),
	            array('class' => 'ajax-loading', 'style' => 'display:none')); ?>
<ul id="mtbf-data-details">

</ul>


<script type="text/javascript">
var SocMtbfSeries = <?php echo json_encode( $releases ); ?>;
</script>
<?php 
    } //if/else no data
} //if/else error message for url
 ?>