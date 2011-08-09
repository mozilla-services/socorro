        <div>
            <dl>
<?php
                for($i =0; $i < count($widgetData[$j]['crashes']); $i++){
                    $topcrash = $widgetData[$j]['crashes'][$i];
                    $link_url =  url::base() . 'report/list?' . html::query_string(array(
                         'range_value' => '2',
                         'range_unit'  => 'weeks',
                         'version'     => $topcrash->product . ':' . $topcrash->version,
                         'signature'   => $topcrash->signature
                     ));
?>
	        <dt><?php echo ($i + 1); ?> <a href="<?php out::H($link_url) ?>" 
                                                                     title="View reports with this crasher signature."><?php echo out::H($topcrash->signature); ?></a></dt>
                <dd><?php echo $topcrash->total; ?></dd>
<?php
                } //for($i =0; $i < ...
?>
            </dl>

<?php
    $product = $widgetData[$j]['name'];
    $version = $widgetData[$j]['version'];
?>
            <a href='<?php echo url::base() . "topcrasher/byversion/" . $product . "/" . $version; ?>' 
                 class='full-report'
                 title='View the full <?php echo $product . " " . $version; ?> report'>Full Report</a>
           
  </div>
<?php 

?>