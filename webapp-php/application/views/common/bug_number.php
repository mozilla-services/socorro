/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<a href="<?= $bug['url'] ?>"
   title="Find more information in Bugzilla"
   class="bug-link" ><?= $bug['id']
?></a><?php
if ( isset($mode) and $mode == 'full') {
  echo ' ', $bug['status'], ' ', out::H($bug['summary']);
}
?>
