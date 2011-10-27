<script type="text/javascript">
    var prodVersMap = <?php echo json_encode($versions_by_product); ?>
</script>

<div class="version-nav query_removemargin">
    <form id="searchform" method="get" action="<?php echo url::base() . "query/query" ?>"
          enctype="application/x-www-form-urlencoded">
    <fieldset>

    <ul>
    <li><label class="basic" for="product">Product</label>
            <select id="product" name="product" size="5" multiple="multiple" class="primary">
                <?php foreach ($all_products as $product): ?>
                    <option value="<?php out::H($product) ?>" <?php echo in_array($product, $params['product']) ? 'selected="selected"' : '' ?>>
                        <?php out::H($product) ?>
                    </option>
                <?php endforeach ?>
            </select>
    </li>
    <li><label class="basic" for="version">Version: </label>
            <select id="version" name="version" size="5" multiple="multiple" class="primary">
                <option value="ALL:ALL">All</option>
                <?php foreach ($all_versions as $row): ?>
                    <?php $row_version  = $row->product . ':' . $row->version; ?>
                    <option value="<?php out::H($row_version) ?>" <?php echo in_array($row_version, $params['version']) ? 'selected="selected"' : '' ?>>
                        <?php out::H($row->product . ' ' . $row->version) ?>
                    </option>
                <?php endforeach ?>
            </select>
    </li>
    <li><label class="basic" for="platform">Operating System</label>
            <select id="platform" name="platform" size="5" multiple="multiple" class="primary">
                <?php foreach ($all_platforms as $row): ?>
                    <option value="<?php out::H($row->id) ?>" <?php echo in_array($row->id, $params['platform']) ? 'selected="selected"' : '' ?>>
                        <?php out::H($row->name) ?>
                    </option>
                <?php endforeach ?>
            </select>
    </li>
    <li><span class="basic label"><a href="#" id="advfiltertoggle" class="not-toggled">Advanced Filters</a></span>

        <div id="advfilter">
            <?php if ($middlewareImplementation != 'ES') { ?>
            <p class="advanced">
                <span class="label">Branch</span>
                <?php foreach ($all_branches as $row): ?>
                    <input type="checkbox" name="branch" value="<?php out::H($row->branch) ?>" <?php echo in_array($row->branch, $params['branch']) ? 'checked' : '' ?>>
                    <?php out::H($row->branch) ?> &nbsp;
                <?php endforeach ?>
            </p>
            <?php } /* end if */ ?>

            <p class="advanced">
               <label for="range_value">For the period of </label>
                  <?php echo form::input(
                      array('size' => '2', 'name'=>'range_value', 'id'=>'range_value'),
                      $params['range_value']
                  )?>
                  <?php echo form::dropdown(
                      'range_unit',
                      array(
                          'hours'=>'Hours', 'days'=>'Days', 'weeks'=>'Weeks'
                      ),
                      $params['range_unit']
                  )?>

                <span id="dateHelp">
                    <label for="date"> before </label>
                    <input type="text" name="date" id="date" size="20" title="This field must be formatted as MM/DD/YYYY HH:MM:SS" value="<?php out::H($params['date']); ?>" />
                </span>
            </p>

            <p class="advanced">
                <label for="query_type">Stack signature</label>
                <input type="hidden" name="query_search" value="signature" />
                <?php
            //used by query and plugin_query
            echo form::dropdown(
                    'query_type',
                    $option_types,
                    $params['query_type']
                ) ?>
                <?php 
                // check whether the signature was passed to the query
                $q_signature = (isset($_GET['signature']) ? $_GET['signature'] : '');
                echo form::input(
                    array('size' => '25', 'name'=>'query', 'id'=>'query', 'value'=>$q_signature),
                    trim($params['query'])
                )?>
            </p>

            <p class="advanced">
                <label for="reason">Crash Reason</label>
                <?php echo form::input(
                    array('size' => '25', 'name'=>'reason', 'id'=>'reason'),
                    trim($params['reason'])
                )?>
            </p>

            <p class="advanced">
            <label for="build_id">Build ID</label>
            <?php echo form::input(
                array('size' => '14', 'name'=>'build_id', 'id'=>'build_id'),
                trim($params['build_id'])
            )?>
            </p>
        <p class="advanced">
        <span class="label">Report Process:</span>
        <span class="radio-item"><label><?= form::radio('process_type', 'any',     $params['process_type'] == 'any'); ?>
            Any</label></span>
        <span class="radio-item"><label><?= form::radio('process_type', 'browser', $params['process_type'] == 'browser'); ?>
            Browser</label></span>
        <span class="radio-item"><label><?= form::radio('process_type', 'plugin',  $params['process_type'] == 'plugin'); ?>
            Plugins Only</label></span>
        <?php /* When out of process plugins support content as a type, we can add:
               <span class="radio-item disabled"><label>Content Only form::radio('process_type', 'plugin', $params['process_type'] == 'plugin'); </label></span> */ ?>

            </p>

        <p class="advanced">
            <span class="label">Report Type:</span>
                <span class="radio-item"><label><?= form::radio('hang_type', 'any',   $params['hang_type'] == 'any'); ?>
            Any</label></span>
        <span class="radio-item"><label><?= form::radio('hang_type', 'crash', $params['hang_type'] == 'crash'); ?>
            Crash</label></span>
        <span class="radio-item"><label><?= form::radio('hang_type', 'hang',  $params['hang_type'] == 'hang'); ?>
            Hang</label></span>
            </p>

            <?php if ($middlewareImplementation != 'ES') { ?>
        <p id="plugin-inputs" class="advanced"><?= form::label('plugin_field', 'Search By Plugin') ?>
                <?= form::dropdown(
                array('id'   => 'plugin_field',
                  'name' => 'plugin_field'),
                array('filename' => 'Filename',
                  'name'     => 'Name'),
                $params['plugin_field']); ?>

            <?= form::dropdown(
                array('id'         => 'plugin_query_type',
                  'name'       => 'plugin_query_type'),
                $option_types,
                $params['plugin_query_type']) ?>

                <?= form::input(array('id'   => 'plugin_query',
                      'name' => 'plugin_query',
                      'size' => '25'),
                    trim($params['plugin_query'])) ?>

            </p>
            <?php } /* end if */ ?>
        </div><!-- /advfilter -->

        <button id="query_submit" type="submit">Filter Crash Reports</button>
        <input type="hidden" name="do_query" value="1" />

        <div id="query_waiting" class="hidden">
            <p class="advanced">
                <img src="<?php echo url::base(); ?>img/loading.png" />
                <i>processing query, please wait...</i>
            </p>
        </div>
        </li>

        </ul>
        </fieldset>
    </form>
</div>

<div id="formspacer"> </div>
