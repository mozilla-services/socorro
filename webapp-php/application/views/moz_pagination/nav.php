<?php defined('SYSPATH') OR die('No direct access allowed.');
/**
 * Slightly updated version of the Kohana - Digg pagination style used in MCC.
 *
 * @preview  « Previous  1 2 … 5 6 7 8 9 10 11 12 … 25 26  Next »
 * @author Ryan Snyder <rsnyder@mozilla.com>
 */
?>

<?php if ($pager->totalPages > 1) { ?>
    <div class="pagination">
        <span class="totalItems"><?php echo number_format($pager->totalItemCount); ?></span> <?= $totalItemText ?></span> &hellip;

<?php
        // Only display pagination when there is > 1 page.
        if ($pager->showPrevious || $pager->showNext) {

			if ($pager->showPrevious) { ?>
                <a href="<?= $navPathPrefix ?><?= $pager->previousPage ?>">← Prev </a>&nbsp;
        	<?php } ?>


        <?php if ($pager->totalPages < 9): /* « Previous  1 2 3 4 5 6 7 8 9 10 11 12  Next » */ ?>

            <?php for ($i = 1; $i <= $pager->totalPages; $i++): ?>
                <?php if ($i == $pager->currentPage): ?>
                    <strong><?= $i ?></strong>
                <?php else: ?>
                    <a href="<?= $navPathPrefix ?><?= $i ?>"><?= $i ?></a>
                <?php endif ?>
            <?php endfor ?>

        <?php elseif ($pager->currentPage < 6): /* « Previous  1 2 3 4 5 6 7 8 9 10 … 25 26  Next » */ ?>

            <?php for ($i = 1; $i <= 6; $i++): ?>
                <?php if ($i == $pager->currentPage): ?>
                    <strong><?= $i ?></strong>
                <?php else: ?>
                    <a href="<?= $navPathPrefix ?><?= $i ?>"><?= $i ?></a>
                <?php endif ?>
            <?php endfor ?>

            &hellip;

            <a href="<?= $navPathPrefix ?><?php echo $pager->totalPages - 1; ?>"> <?php echo $pager->totalPages - 1 ?></a>
            <a href="<?= $navPathPrefix ?><?php echo $pager->totalPages; ?>"> <?php echo $pager->totalPages ?></a>

        <?php elseif ($pager->currentPage > $pager->totalPages - 5): /* « Previous  1 2 … 17 18 19 20 21 22 23 24 25 26  Next » */ ?>

           <a href="<?= $navPathPrefix ?>1"> 1</a>
           <a href="<?= $navPathPrefix ?>2"> 2</a>

           &hellip;

           <?php for ($i = $pager->totalPages - 5; $i <= $pager->totalPages; $i++): ?>
               <?php if ($i == $pager->currentPage): ?>
                   <strong><?php echo $i ?></strong>
               <?php else: ?>
                   <a href="<?= $navPathPrefix ?><?= $i ?>"><?php echo $i ?></a>
               <?php endif ?>
           <?php endfor ?>

           <?php else: /* « Previous  1 2 … 5 6 7 8 9 10 11 12 13 14 … 25 26  Next » */ ?>

               <a href="<?= $navPathPrefix ?>1"> 1</a>
               <a href="<?= $navPathPrefix ?>2"> 2</a>

               &hellip;

               <?php for ($i = $pager->currentPage - 2; $i <= $pager->currentPage + 2; $i++): ?>
                   <?php if ($i == $pager->currentPage): ?>
                       <strong><?php echo $i ?></strong>
                   <?php else: ?>
                       <a href="<?= $navPathPrefix ?><?= $i ?>"><?php echo $i ?></a>
                   <?php endif ?>
               <?php endfor ?>

               &hellip;

               <a href="<?= $navPathPrefix ?><?php echo $pager->totalPages - 1 ?>"> <?php echo $pager->totalPages - 1 ?></a>
               <a href="<?= $navPathPrefix ?><?php echo $pager->totalPages ?>"> <?php echo $pager->totalPages ?></a>

        <?php endif ?>


        <?php if ($pager->showNext) { ?>
                <a href="<?= $navPathPrefix ?><?= $pager->nextPage ?>">Next →</a>
        <?php } ?>

	</div>
	<?php } ?>
<?php } ?>
