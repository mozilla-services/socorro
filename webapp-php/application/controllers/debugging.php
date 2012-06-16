<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * This controller is for debugging stage or production ONLY
 * ***NOTE*** should be empty most of the time. Don't leave any
 * wacky code in the tree, which could become an exploit.
 */
class Debugging_Controller extends Controller {

    public function index() {}
}
