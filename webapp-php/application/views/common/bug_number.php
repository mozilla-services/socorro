<?php
                                  if (! $bug['open']) {
				      echo '<span class="strike">';
				  } ?>
				    <a href="<?= $bug['url'] ?>"
                                       title="<?= $bug['status']?> <?= $bug['resolution']?> <?= out::H($bug['summary'])?>"><?= $bug['id'] ?></a><?php 
				  if (! $bug['open']) {
				      echo "</span>";
				  }
?>