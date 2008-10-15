<?php slot::start('head') ?>
    <title>Crash Reports</title>

    <?php echo html::stylesheet(array(
        'css/datePicker.css',
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>

    <?php echo html::script(array(
        'js/jquery/jquery-1.2.1.js',
        'js/jquery/date.js',
        'js/jquery/plugins/ui/jquery.datePicker.js',
        'js/jquery/plugins/ui/jquery.tablesorter.min.js'
    ))?>

    <script type="text/javascript">
        $(function() {
            Date.format='yyyy-mm-dd';
            $('.date-pick').datePicker();
            $('.date-pick').dpSetStartDate('2007-01-01');
            $('#signatureList').tablesorter(); 
        });
    </script>
<?php slot::end() ?>

<h1 class="first">Search Crash Reports</h1>

<form name="query" method="GET" action="<?php echo url::base() ?>">
    <input type="hidden" name="do_query" value="1" />

    <p>
        <label for="product">Product: </label>
        <select name="product" size="4" multiple="multiple">
            <?php foreach ($all_products as $row): ?>
                <option value="<?php out::H($row->product) ?>" <?php echo in_array($row->product, $params['product']) ? 'selected="selected"' : '' ?>>
                    <?php out::H($row->product) ?>
                </option>
            <?php endforeach ?>
        </select>

        <label for="branch">Branch: </label>
        <select name="branch" size="4" multiple="multiple">
            <?php foreach ($all_branches as $row): ?>
                <option value="<?php out::H($row->branch) ?>" <?php echo in_array($row->branch, $params['branch']) ? 'selected="selected"' : '' ?>>
                    <?php out::H($row->branch) ?>
                </option>
            <?php endforeach ?>
        </select>

        <label for="version">Version: </label>
        <!-- Want some fancy AJAX goodness here! -->
        <select name="version" size="4" multiple="multiple">
            <?php foreach ($all_versions as $row): ?>
                <?php $row_version  = $row->product . ':' . $row->version; ?>
                <option value="<?php out::H($row_version) ?>" <?php echo in_array($row_version, $params['version']) ? 'selected="selected"' : '' ?>>
                    <?php out::H($row->product . ' ' . $row->version) ?>
                </option>
            <?php endforeach ?>
        </select>

        <label for="platform">Platform: </label>
        <select name="platform" size="<?php echo count($all_platforms) ?>" multiple="multiple">
            <?php foreach ($all_platforms as $row): ?>
                <option value="<?php out::H($row->id) ?>" <?php echo in_array($row->id, $params['platform']) ? 'selected="selected"' : '' ?>>
                    <?php out::H($row->name) ?>
                </option>
            <?php endforeach ?>
        </select>
    </p>

    <p>
        <?php echo form::dropdown(
            'query_search',
            array(
                'signature' => 'Stack Signature',
                'stack'     => 'One of the top 10 Stack Frames'
            ),
            $params['query_search']
        ) ?>
        <?php echo form::dropdown(
            'query_type',
            array(
                'contains'   => 'contains',
                'exact'      => 'is exactly',
                'startswith' => 'starts with'
            ),
            $params['query_type']
        ) ?>
        <?php echo form::input(
            array('size' => '40', 'name'=>'query', 'id'=>'query'), 
            $params['query']
        )?>
    </p>

    <p>
        <label for="date">
            Occurring before date (default: now, format yyyy-mm-dd HH:MM:SS):
        </label>
        <?php echo form::input(
            array('size' => '20', 'name'=>'date', 'id'=>'date', 'class'=>'date-pick'), 
            $params['date']
        )?>
        <br />
        <label for="range_value">Date range: </label>
        <?php echo form::input(
            array('size' => '2', 'name'=>'range_value', 'id'=>'range_value'), 
            $params['range_value']
        )?><?php echo form::dropdown(
            'range_unit',
            array(
                'hours'=>'hours', 'days'=>'days', 'weeks'=>'weeks', 'months'=>'months'
            ),
            $params['range_unit']
        )?>
    </p>

    <input type="submit" />
</form>

<?php if ($params['do_query'] !== FALSE): ?>
    <h2>Query Results</h2>

    <?php 
        View::factory('common/prose_params', array(
            'params'    => $params,
            'platforms' => $all_platforms
        ))->render(TRUE) 
    ?>

    <?php 
        View::factory('common/list_by_signature', array(
            'params'    => $params,
            'platforms' => $all_platforms,
            'reports'   => $reports 
        ))->render(TRUE) 
    ?>

<?php endif ?>
