<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html lang="en">

    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <link href="<?php echo url::base() ?>css/layout.css" rel="stylesheet" type="text/css" media="screen" />
        <link href="<?php echo url::base() ?>css/style.css" rel="stylesheet" type="text/css" media="all" />
        <link href="<?php echo url::base() ?>favicon.ico" rel="icon" type="image/png" />
        <?php slot::output('head') ?>
    </head>

    <body>

        <!-- site header -->
        <div id="header">
            <h1><a href="<?php echo url::base() ?>">Mozilla Crash Reports</a></h1>
            <div id="menu">
                <form id="quickfind" action="<?php echo url::base() ?>report/find">
                    <input type="text" size="24" name="id" id="crash-id"/>
                    <input type="submit" value="Go to Report" />
                </form>
                <ul>
                    <li><a href="<?php echo url::base() ?>">Find a Report</a></li>
                    <li><a href="<?php echo url::base() ?>topcrasher">Top Crashers</a></li>
                </ul>
            </div>
        </div>
        <!-- end site header -->

        <div id="top">
            <?php slot::output('top') ?>
        </div>

        <div id="content"><?php echo $content ?></div>

        <!-- site footer -->
        <div id="footer">
            <ul>
                <li><a href="http://code.google.com/p/socorro/">Project Info</a></li>
                <li><a href="http://code.google.com/p/socorro/source">Get the Source</a></li>
                <li><a href="http://wiki.mozilla.org/Breakpad">Breakpad Wiki</a></li>
            </ul>
        </div>
        <!-- end site footer -->

    </body>
</html>
