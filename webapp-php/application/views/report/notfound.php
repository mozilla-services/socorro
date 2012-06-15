<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
    <div id="mainbody">
            <div class="page-heading">
                <h2>Crash Not Found</h2>
            </div>
            <div class="panel">
                <div class="body notitle">
                <p>We couldn't find the OOID you're after. If you recently submitted this crash, it may still be in the queue.</p>

                <p>If you believe this message is an error, please
                submit a <a href="https://bugzilla.mozilla.org/enter_bug.cgi?product=Webtools&component=Socorro&bug_file_loc=<?php echo urlencode($_SERVER['SCRIPT_URI']); ?>">Bugzilla ticket</a> describing what happened, and please include the URL for this page.</p>
                </div>
            </div>
    </div>
