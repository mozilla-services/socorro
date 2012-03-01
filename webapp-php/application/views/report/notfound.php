    <div id="mainbody">
    <?php
        /**
         * The only of the $_SERVER elements that keeps the correct protocol 
         * i.e. http(s) is the referer constant but, that does not work for our 
         * requirements here hence, we use the method below to ensure our bug_file_loc 
         * URL's protocol matches the protocol it was served on.
         */
        $protocol = (!empty($_SERVER['HTTPS']) ? "https://" : "http://");
        $server_name = $_SERVER['SERVER_NAME'];
        $path = $_SERVER['REQUEST_URI'];
        
        $current_url = $protocol . $server_name . $path;
    ?>
            <div class="page-heading">
                <h2>Crash Not Found</h2>
            </div>
            <div class="panel">
                <div class="body notitle">
                <p>We couldn't find the OOID you're after. If you recently submitted this crash, it may still be in the queue.</p>

                <p>If you believe this message is an error, please
                submit a <a href="https://bugzilla.mozilla.org/enter_bug.cgi?product=Webtools&component=Socorro&bug_file_loc=<?php echo urlencode($current_url); ?>">Bugzilla ticket</a> describing what happened, and please include the URL for this page.</p>
                </div>
            </div>
    </div>
