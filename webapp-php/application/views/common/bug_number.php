<?php
                                  if (! $bug['open']) {
				      echo "<strike>";
				  } ?>
				    <a href="<?= $bug['url'] ?>"
                                       title="<?= $bug['status']?> <?= $bug['resolution']?> <?= $bug['summary']?>"><?= $bug['id'] ?></a><?php 
				  if (! $bug['open']) {
				      echo "</strike>";
				  }
?>