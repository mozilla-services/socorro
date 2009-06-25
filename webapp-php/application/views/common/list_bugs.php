                           <div class="bug_ids_expanded_list">						      
						      <h3>Bugs for <code><?= out::H($signature) ?></code></h3>
                                  <dl class="sorted_bug_ids <?= $mode ?>"><?php
			          $last_res = NULL;
				  $open_ul = FALSE;
				  foreach ($bugs as $bug) {
				      
				      if ($bug['resolution'] !== $last_res) { 
					  $last_res = $bug['resolution']; 
					  if ($open_ul) { ?>
					    </ul></dd>
				    <?php } else {
					    $open_ul = TRUE;
					  } ?>
					  <dt><?php echo $bug['open'] ? 'OPEN' : $bug['resolution'] ?></dt><dd><ul class="full_bug_ids <?= $mode ?>">
			        <?php } ?>
				      <li><?php View::factory('common/bug_number')
                                                    ->set('bug', $bug)
                                                    ->set('mode', $mode)
                                                    ->render(TRUE);?></li><?php 
				  }
                            ?></ul></dd></dl></div>