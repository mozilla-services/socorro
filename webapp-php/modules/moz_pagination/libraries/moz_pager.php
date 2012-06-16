<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Mozilla WebDev pagination
 */
class MozPager
{
    public function __construct($itemsPerPage, $totalItemCount, $currentPage=1)
    {
        $this->totalItemCount = $totalItemCount;
        $this->itemsPerPage = $itemsPerPage;
        $this->currentPage = $currentPage;

        $this->totalPages = ceil($totalItemCount / $itemsPerPage);

        $this->nextPage = $this->currentPage + 1;
        $this->showNext = ($currentPage < $this->totalPages);

        $this->previousPage = $this->currentPage - 1;
        $this->showPrevious = ($this->currentPage > 1);

        $this->offset = ($this->currentPage - 1) * $this->itemsPerPage;
    }
}
?>
