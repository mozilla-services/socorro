     <?php if (isset($has_errors) && $has_errors) { ?>
        <h3>Errors</h3>
        <p>Please <strong>fix the following errors</strong> and try again.</p>
        <ul class="errors">
          <?php foreach ($errors as $key => $value) { ?>
            <li><?= $value ?></li>
          <?php } ?>
        </ul>
      <?php } ?>
