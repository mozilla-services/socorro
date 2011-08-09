<?php /* Using this widget requires:
$widgetName - Show in heading
$widgetData - array of elements with a 'label' key in each item
$subWidget - the template name of the subwidget which will render each item.
*/ 

$widgetClasses = "topcrashers";
if ( isset($extraClasses) ) {
    $widgetClasses .= " $extraClasses";
 }
?>

<div class="<?php echo $widgetClasses ?>">
  <h4><?php echo $widgetName ?></h4>
  <div class="topcrashersaccord">

<?php    
    for($j=0; $j < count($widgetData); $j++){    
?>
        <h3><?php echo $widgetData[$j]['label'] ?></h3>
<?php  View::factory($subWidget, array('j' => $j, 'widgetData' => $widgetData ))->render(TRUE); ?>
<?php
    } //for($j=0; $j < count($widgetData); $j++){        
?>
  </div> <!-- /topcrashersaccord -->
</div> <!-- /TOPCRASHERS -->
