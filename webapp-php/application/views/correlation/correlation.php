<div class='correlation'><h3><?= html::specialchars($details['crash_reason'])?> (<?= $details['count'] ?>)</h3>
<pre><?= join("\n", $details['correlations']) ?></pre></div>