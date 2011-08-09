<a href="<?= $bug['url'] ?>"
   title="Find more information in Bugzilla" 
   class="bug-link" ><?= $bug['id']
?></a><?php
if ( isset($mode) and $mode == 'full') {
  echo ' ', $bug['status'], ' ', out::H($bug['summary']);
}
?>
