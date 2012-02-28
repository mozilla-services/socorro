<?php slot::start('head') ?>
    <title>Branch Data Source - Socorro Admin</title>
<?php slot::end() ?>

<div class="page-heading">
    <h2>Branch Data Sources</h2>
</div>

<div class="panel">
    <div class="body notitle">
        <div class="admin">
        <p>Manage thy branch data sources here.  Information about maintaining this data can be found in the <a href="https://wiki.mozilla.org/Socorro/SocorroUI/Branches_Admin">Socorro</a> wiki.</p>

            <div id="data_sources">
                <ul id="data_sources_nav">
                    <li><a href="#missingentries"><span>Missing Entries</span></a></li>
                    <li><a href="#incompleteentries"><span>Incomplete Entries</span></a></li>
                    <li><a href="#products"><span>Products</span></a></li>
                    <li><a href="#noncurrententries"><span>Non-Current Entries</span></a></li>
                </ul>

                <p id="loading-bds"><img src="/img/icons/ajax-loader.gif" width="" height="" alt="loading animation" /></p>

                <div id="missingentries" class="ui-tabs-hide">
                    <?php include Kohana::find_file('views', 'admin/branch_data_sources/missing_entries') ?>
                </div>

                <div id="incompleteentries" class="ui-tabs-hide">
                    <?php include Kohana::find_file('views', 'admin/branch_data_sources/incomplete_entries') ?>
                </div>

                <div id="products" class="ui-tabs-hide">
                    <?php include Kohana::find_file('views', 'admin/branch_data_sources/products') ?>
                </div>

                <div id="noncurrententries" class="ui-tabs-hide">
                    <?php include Kohana::find_file('views', 'admin/branch_data_sources/non_current_entries') ?>
                </div>
            </div>

            <div id="add_version" name="add_version" class="add_item">
                <p>Fill out this form to add a new product version.</p>
                <form action="" id="form_add_version" name="form_add_version" method="post">
                <input type="hidden" name="action_add_version" value="1">

                <table>
                    <tr><td>Product: </td><td><input type="text" id="product" name="product" value="" /></p>
                    <tr><td>Version: </td><td><input type="text" id="version" name="version" value="" /></p>
                    <tr><td>Start Date: </td><td><input class="text" type="text" id="start_date" name="start_date" value="<?php echo html::specialchars($default_start_date); ?>" /></td></tr>
                    <tr><td>End Date:</td><td><input class="text" type="text" id="end_date" name="end_date" value="<?php echo html::specialchars($default_end_date); ?>" /></td></tr>
                    <tr><td>Featured:   </td><td><input type="checkbox" id="featured" name="featured" value="t" /></td></tr>
                    <tr><td>Throttle:   </td><td><input class="text" type="text" id="throttle" name="throttle" value="<?php echo $throttle_default; ?>" />% [<a href="http://code.google.com/p/socorro/wiki/SocorroUIAdmin#Throttle" target="_NEW">?</a>]</td></tr>
                </table>
                <p id="add_submit"><input type="submit" name="submit" value="Add Product Version" onclick="hideShow('add_submit', 'add_submit_progress');" /></p>
                <p id="add_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
                </form>
            </div>

            <div id="update_product_version" name="update_product_version" class="add_item">
                <p>Fill out this form to update an existing product version.</p>
                <form action="" id="form_update_version" name="form_update_version" method="post">
                    <input type="hidden" name="action_update_version" value="1">

                    <table>
                    <tr><td>Product: </td>
                        <td>
                            <input type="hidden" id="update_product" name="update_product" value="" />
                            <span id="update_product_display" name="update_product_display"></span>
                        </td>
                    </tr>
                    <tr><td>Version: </td>
                        <td>
                            <input type="hidden" id="update_version" name="update_version" value="" />
                            <span id="update_version_display" name="update_version_display"></span>
                        </td>
                    </tr>
                    <tr><td>Start Date: </td><td><input class="text" type="text" id="update_start_date" name="update_start_date" value="" /></td></tr>
                    <tr><td>End Date:   </td><td><input class="text" type="text" id="update_end_date" name="update_end_date" value="" /></td></tr>
                    <tr><td>Featured:   </td><td><input type="checkbox" id="update_featured" name="update_featured" value="t" /></td></tr>
                    <tr><td>Throttle:   </td><td><input class="text" type="text" id="update_throttle" name="update_throttle" value="<?php echo $throttle_default; ?>" />% [<a href="https://wiki.mozilla.org/Socorro/SocorroUI/Branches_Admin#Throttle" target="_NEW">?</a>]</td></tr>
                    </table>

                    <p id="update_submit"><input type="submit" name="submit" value="Update Product Version" onclick="hideShow('update_submit', 'update_submit_progress');" /></p>
                    <p id="update_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
                </form>
            </div>

            <div id="delete_product_version" name="delete_product_version" class="add_item">
                <p>Do you really want to delete this product version?</p>
                <form action="" id="form_delete_version" name="form_delete_version" method="post">
                    <input type="hidden" name="action_delete_version" value="1">
                    <span class="push_right">
                    Product:
                        <input type="hidden" id="delete_product" name="delete_product" value="" />
                        <span id="delete_product_display" name="delete_product_display"></span>
                    </span>

                    <span class="push_right">
                    Version:
                        <input type="hidden" id="delete_version" name="delete_version" value="" />
                        <span id="delete_version_display" name="delete_version_display"></span>
                    </span>

                    <p id="delete_submit"><input type="submit" name="submit" value="Yes, I want to Delete this Product Version" onclick="hideShow('delete_submit', 'delete_submit_progress');" /></p>
                    <p id="delete_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
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
