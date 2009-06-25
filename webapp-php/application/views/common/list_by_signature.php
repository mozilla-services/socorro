<table id="signatureList" class="tablesorter">
    <thead>
        <tr>
            <th>Rank</th>
            <th>Signature</th>
            <?php if (count($platforms) > 1): ?><th>#</th><?php endif ?>
            <?php foreach ($platforms as $platform): ?>
                <th><?php out::H(substr($platform->name, 0, 3)) ?></th>
            <?php endforeach ?>
	   <?php if (isset($sig2bugs)) {?>
               <th class="bugzilla_numbers">Bugzilla Ids</th>
           <?php } ?>
        </tr>
    </thead>
    <tbody>
        <?php $row = 1 ?>
        <?php foreach ($reports as $report): ?>
            <tr class="<?php echo ( ($row-1) % 2) == 0 ? 'even' : 'odd' ?>">
                <td><?php out::H($row) ?></td>
                <td>
                    <?php
                        $url_params = $params;
                        $url_params['signature'] = $report->signature;
                        $url = url::base().'report/list?'.html::query_string($url_params);
                    ?><a href="<?php out::H($url) ?>" title="View reports with this signature."><?php out::H($report->signature) ?></a>
                </td>
                <?php if (count($platforms) > 1): ?><th><?php out::H($report->count) ?></th><?php endif ?>
                <?php foreach ($platforms as $platform): ?>
                    <td><?php out::H($report->{'is_'.$platform->id}) ?></td>
                <?php endforeach ?>
               <?php if (isset($sig2bugs)) {?>
                    <td>
		    <?php if (array_key_exists($report->signature, $sig2bugs)) { 
			      $bugs = $sig2bugs[$report->signature];
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
						      'signature' => $report->signature,
						      'bugs' => $bugs,
						      'mode' => 'popup'
				  ))->render(TRUE);
		              }
                         } ?>
                    </td>
               <?php } ?>
            </tr>
            <?php $row += 1 ?>
        <?php endforeach ?>
    </tbody>
</table>
