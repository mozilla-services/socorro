<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>

<div class="page-heading">
	<h2>Admin Page</h2>
</div>

<div class="panel">
    <div class="title">
        <h2>Control Panels</h2>
    </div>
    <div class="body">
        <h3>Data Management</h3>
        <p><a href="<?php echo url::site('admin/branch_data_sources'); ?>">Branch Data Sources</a></p>
        <p><a href="<?php echo url::site('admin/os_names'); ?>">OS Names</a></p>
        <p><a href="<?php echo url::site('admin/os_matches'); ?>">OS Name Matching</a></p>
        <h3>Post Crash</h3>
        <p><a href="<?php echo url::site('admin/email'); ?>">Email Users</a></p>
    </div>
</div>

