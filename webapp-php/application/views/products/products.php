

<div class="panel">
	<div class="title">
		<h2>Mozilla Products in Crash Reporter</h2>
    </div>
    
    <div class="body">
    <p>
        <ul>
        <?php foreach ($products as $product) { ?>
            <li><a href="<?php echo url::site('products/'.$product); ?>"><?php out::H($product); ?></a></li>
        <?php } ?>
        </ul>
    </p>
    </div>

</div>
