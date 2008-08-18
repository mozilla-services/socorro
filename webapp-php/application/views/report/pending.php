<?php slot::start('head') ?>
    <title>Please wait... we are processing your report.</title>
    <meta http-equiv="refresh" content="21; url=<?php out::H( url::base() . '/report/index/' . $uuid + '?p=1' ) ?>"/>
<?php slot::end() ?>

<h1 class="loading">Your report is being processed</h1>
<ul>
    <li>We've given <a href="<?php out::H( url::base() . '/report/index/' . $uuid + '?p=1' ) ?>">your report</a> priority</li>
    <li>Your report should be ready in a minute</li>
    <li>This page will refresh and display your report's status</li>
    <li>When your report has been processed, we will redirect you to your
    report</li>
</ul>

<?php if ($job): ?>
    <h2>Queue Info</h2>
    <dl>
        <dt>ID</dt>
            <dd><?php out::H( $job->uuid ) ?></dd>
        <dt>Time Queued</dt>
            <dd><?php out::H( $job->queueddatetime ) ?></dd>
        <?php if ($job->starteddatetime): ?>
            <dt>Time Started</dt>
                <dd><?php out::H( $job->starteddatetime ) ?></dd>
        <?php endif ?>
        <?php if ($job->message): ?>
            <dt>Message</dt>
                <dd><?php out::H( $job->message ) ?></dd>
        <?php endif ?>
    </dl>
<?php endif ?>
