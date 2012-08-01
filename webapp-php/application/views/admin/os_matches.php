<?php slot::start('head') ?>
    <title>Supported OS list - Socorro Admin</title>
<?php slot::end() ?>

<div class="page-heading">
    <h2>Supported OS list</h2>
</div>

<div class="panel">
    <div class="body notitle">
        <div class="admin">
            <p>Manage supported OSes here.</p>

            <?php if (isset($os_name_matches) && sizeof($os_name_matches) > 0) { ?>
                <table class="branch">
                    <thead>
                        <tr>
                            <th>OS Family</th>
                            <th>Pattern</th>
                            <th>Delete?</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($os_name_matches as $os_name_match) { ?>
                            <tr>
                                <td class="text"><?php echo html::specialchars($os_name_match->os_name); ?></td>
                                <td class="text"><?php echo html::specialchars($os_name_match->pattern); ?></td>
                                <td class="action"><a href="#delete_os_match"
                                                      onclick="deleteOsMatch(
                                                                   '<?php echo html::specialchars($os_name_match->os_name) ?>',
                                                                   '<?php echo html::specialchars($os_name_match->pattern) ?>'
                                                                   )">delete</a></td>
                            </tr>
                        <?php } ?>
                    </tbody>
                </table>
            <?php } else { ?>
                 <!-- TODO: add information about the OS names in the reports table -->
                 <p>Table is empty! All reports are throttled!</p>
            <?php } ?>

            <p><a href="#form_add_os"
                  onclick="addOsMatch(); return false;">Add</a></p>
            
            <div id="add_os_match" class="add_item form_container">
                <p>Fill out this form to add a new supported OS</p>
                <form action="" method="post">
                    <input type="hidden" name="action_add_os_match" value="1" />
                    <table>
                        <tr>
                            <td>OS Family
                                (<small>you may manage OS families
                                        <a href="./os_names">here</a></small>):
                            </td>
                            <td>
                                <select name="os_family">
                                <?php foreach ($os_names as $os_name) { ?>
                                    <option value="<?php echo $os_name->os_name; ?>">
                                        <?php echo $os_name->os_name; ?>
                                    </option>
                                <?php } ?>
                                </select>
                            </td>
                        </tr>
                        <tr>
                            <td>Pattern ('?' <small>for any symbol</small>,
                                         '%' <small>for any phrase</small>):</td>
                            <td><input type="text" name="pattern" value="" /></td>
                        </tr>
                    </table>
                    <p id="add_submit"><input type="submit" name="submit" value="Add Supported OS" onclick="hideShow('add_submit', 'add_submit_progress');" /></p>
                    <p id="add_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
                </form>
            </div>

            <div id="delete_os_match" class="add_item form_container">
                <p>Are you sure you want to delete pattern
                    <span id="current_os_family"></span>&nbsp;&mdash;
                    <span id="current_os_pattern"></span>?</p>
                <form action="" method="post">
                    <input type="hidden" name="action_delete_os_match" value="1" />
                    <input type="hidden" name="os_family" value="" id="delete_os_family_value" />
                    <input type="hidden" name="pattern" value="" id="delete_pattern_value" />
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
