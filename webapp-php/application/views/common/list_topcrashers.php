<?php if (count($top_crashers) > 0) { ?>
<div>
    Top <?php echo count($top_crashers) ?> Crashing Signatures
    <span class="start-date"><?php out::H(date('m/d H:i', $start)) ?></span> through
    <span class="end-date"><?php out::H(date('m-d H:i', $last_updated)) ?></span>.
    The  report covers <span class="percentage" title="<?=$percentTotal?>"><?= number_format($percentTotal * 100, 2)?>%</span> of all <span class="total-num-crashes" title="<?= $total_crashes ?>"><?= number_format($total_crashes) ?></span> crashes during this period.
	<div id="duration-nav">
  	  <h3>Other Periods:</h3>
  	  <ul>
	<?php foreach ($other_durations as $d) { ?>
	    <li><a href="<?= $duration_url . '/' . $d ?>"><?= $d ?> Days</a></li>
	<?php }?>
	</ul></div>
        <table id="signatureList" class="tablesorter">
            <thead>
                <tr>
                    <th>Rank</th>
	            <th>% of Total</th>
                    <th>Signature</th>	  
                    <th>Count</th>
                    <th>Win</th>
                    <th>Mac</th>
                    <th>Lin</th>
           <?php if (isset($sig2bugs)) {?>
               <th class="bugzilla_numbers">Bugzilla Ids</th>
           <?php } ?>
                </tr>
            </thead>
            <tbody>
                <?php $row = 1 ?>
                <?php foreach ($top_crashers as $crasher): ?>
                    <?php
                        $nonBlankSignature = $crasher->signature?$crasher->signature:'(signature unavailable)';
                        $nonBlankSigParams = array(
                            'range_value' => '2',
                            'range_unit'  => 'weeks',
                            'signature'   => $nonBlankSignature
			    );
                        if (property_exists($crasher, 'version')) {
			    $nonBlankSigParams['version'] = $crasher->product . ':' . $crasher->version;
			} else {
			    $nonBlankSigParams['branch'] = $crasher->branch;
			}

                        $link_url =  url::base() . 'report/list?' . html::query_string($nonBlankSigParams);
                        $percent = '';
                        if (property_exists($crasher, 'percent')) {
                            $percent = $crasher->percent;
                        }
                    ?>
                    <tr class="<?php echo ( ($row-1) % 2) == 0 ? 'even' : 'odd' ?>">
                        <td><?php out::H($row) ?></td>
		        <td><span class="percentOfTotal"><?php echo $percent ?></span></td>
                        <td><a href="<?php out::H($link_url) ?>" title="View reports with this crasher."><?php out::H($nonBlankSignature) ?></a></td>
                        <td><?php out::H($crasher->total) ?></td>
                        <td><?php out::H($crasher->win) ?></td>
                        <td><?php out::H($crasher->mac) ?></td>
                        <td><?php out::H($crasher->linux) ?></td>


               <?php if (isset($sig2bugs)) {?>
                    <td>
		    <?php if (array_key_exists($crasher->signature, $sig2bugs)) { 
			      $bugs = $sig2bugs[$crasher->signature];
			      for ($i = 0; $i < 3 and $i < count($bugs); $i++) {
				  $bug = $bugs[$i];
				  View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
				  echo ", ";
			      } ?>
                              <div class="bug_ids_extra">
                        <?php for ($i = 3; $i < count($bugs); $i++) { 
				  $bug = $bugs[$i];
                                  View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
                              } ?>
			      </div>
			<?php if (count($bugs) > 0) { ?>
			      <a href='#' title="Click to See all likely bug numbers" class="bug_ids_more">More</a>
                            <?php View::factory('common/list_bugs', array(
						      'signature' => $crasher->signature,
						      'bugs' => $bugs,
						      'mode' => 'popup'
				  ))->render(TRUE);
		              }
                         } ?>
                    </td>
               <?php } ?>



                        <?php $row+=1 ?>
                    </tr>
                <?php endforeach ?>
            </tbody>
        </table>
    </div>
    <?php View::factory('common/csv_link_copy')->render(TRUE); ?>
<?php } else { ?>
    <p>No results were found.</p>
<?php } ?>