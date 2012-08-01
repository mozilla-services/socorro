<?php slot::start('head') ?>
    <title>OS Families - Socorro Admin</title>
<?php slot::end() ?>

<div class="page-heading">
    <h2>OS Families</h2>
</div>

<div class="panel">
    <div class="body notitle">
        <div class="admin">
            <?php if (isset($os_names) && sizeof($os_names) > 0) { ?>
                <table class="branch">
                    <thead>
                        <tr>
                            <th>OS&nbsp;Name</th>
                            <th>Short&nbsp;Name</th>
                            <th>Delete?</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($os_names as $os_name) { ?>
                            <tr>
                                <td class="text">
                                    <?php echo html::specialchars($os_name->os_name); ?>
                                </td>
                                <td class="action">
                                    <?php echo html::specialchars($os_name->os_short_name); ?>
                                </td>
                                <td class="text">
                                    <a href="#delete_os_name"
                                       onclick="deleteOsName(
                                           '<?php echo html::specialchars($os_name->os_name); ?>',
                                           '<?php echo html::specialchars($os_name->os_short_name); ?>')">delete</a></td>
                            </tr>
                        <?php } ?>
                    </tbody>
                </table>
            <?php } ?>

            <p><a href="#form_add_os_name"
                  onclick="addOsName(); return false;">Add</a></p>
            
            <div id="add_os_name" class="add_item form_container">
                <p>Fill out this form to add a new OS name</p>
                <form action="" id="form_add_os_name" name="form_add_os_name" method="post">
                    <input type="hidden" name="action_add_os_name" value="1">
                    <table>
                        <tr>
                            <td>OS Name:</td>
                            <td><input type="text" id="add_os_name_value"
                                       name="os_name" value="" /></td>
                        </tr>
                        <tr>
                            <td>Short Name</td>
                            <td><input type="text" id="add_os_short_name_value"
                                       name="os_short_name" value="" /></td>
                        </tr>
                    </table>
                    <p id="add_submit">
                        <input type="submit" name="submit" value="Add OS Name"
                               onclick="hideShow('add_submit', 'add_submit_progress');" />
                    </p>
                    <p id="add_submit_progress" style="display:none;">
                        <img src="<?php echo url::site(); ?>img/loading.png" />
                        <em>please wait...</em>
                    </p>
                </form>
            </div>

            <div id="delete_os_name" class="add_item form_container">
                <p>Are you sure you want to delete record for
                   <span id="selected_os_name"></span>?</p>
                <form action="" id="form_delete_os_name" name="form_delete_os_name" method="post">
                    <input type="hidden" name="action_delete_os_name" value="1" />
                    <input type="hidden" id="delete_os_name_value" name="os_name" />
                    <input type="hidden" id="delete_os_short_name_value" name="os_short_name" />
                    <p id="delete_submit">
                        <input type="submit"
                               name="submit"
                               value="Delete"
                               onclick="hideShow('delete_submit', 'delete_submit_progress');" />
                    </p>
                    <p id="delete_submit_progress" style="display:none;">
                        <img src="<?php echo url::site(); ?>img/loading.png" />
                        <em>please wait...</em>
                    </p>
                </form>
            </div>
        </div>
    </div>
</div>

<?php echo html::script(array(
    'js/jquery/plugins/ui/jquery-ui-1.8.16.tabs.min.js',
    'js/jquery/plugins/jquery.simplebox.min.js',
    'js/jquery/plugins/jquery.cookie.js'
))?>
