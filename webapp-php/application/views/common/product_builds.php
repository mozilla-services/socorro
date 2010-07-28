
<div class="page-heading">
    <h2>
            Nightly Builds for <?php out::H($product) ?>
            <?php if (isset($version) && !empty($version)) out::H($version); ?>
    </h2>
</div>

<div class="panel">
    <div class="body notitle">    

<?php if (isset($dates) && !empty($dates)) { ?>
    <?php if (isset($builds) && !empty($builds)) { ?>

        <p>The following nightly builds were scraped from the <a href="http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/">Mozilla Nightly Builds FTP site</a>.</p>
        
        <table class="builds">
            <th>Date</th>
            <th>Version</th>
            <th>Platforms</th>
    <?php         
            foreach ($dates as $date) {
                foreach ($versions as $version) {
    ?>
                    <tr>
                    <td><?php echo date("M dS, Y", strtotime($date)); ?></td>
                    <td><?php echo html::specialchars($product) . ' ' . html::specialchars($version); ?></td>
                    <td>
                <?php 
                    $b = '';
                    foreach ($builds as $build) {
                        if (strstr($build->date, $date) && $build->version == $version) {
                            $product = ($build->product == 'seamonkey') ? 'SeaMonkey' : ucfirst($build->product);
                            $product_version = $product . ":" . $build->version;
                            
                            $b .= '<a class="builds" href="' . url::base() . 'query/query?'.
                                  'product=' . html::specialchars(rawurlencode($product)) . '&' .
                                  'version=' . html::specialchars(rawurlencode($product_version)) . '&' .
                                  'build_id=' . html::specialchars(rawurlencode($build->buildid)) .'&' .
                                  'do_query=1">' . html::specialchars($build->platform) . '</a>';
                        }
                    }
                    
                    if (!empty($b)) {
                        echo $b;
                    } else {
                        echo 'No builds were found.';
                    }
                ?>
                    </td></tr>
                <?php 
                }
            }
        ?>

            </table>

            <p>
                <a href="<?php echo url::base() . $url_rss; ?>"><img src="<?php echo url::base(); ?>img/feed-icon16x16.png"></a> 
                <a href="<?php echo url::base() . $url_rss; ?>">Subscribe</a>
            </p>

        </div>
    <?php
       } else {
           echo '<p>No results were found.</p>';
       }
    } 
?>

    </div>
</div>
