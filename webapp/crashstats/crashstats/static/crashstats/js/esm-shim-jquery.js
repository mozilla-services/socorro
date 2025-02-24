// # This Source Code Form is subject to the terms of the Mozilla Public
// # License, v. 2.0. If a copy of the MPL was not distributed with this
// # file, You can obtain one at https://mozilla.org/MPL/2.0/.

// This jQuery shim is necessary as a separate file because imports are hoisted/evaluated before we can assign the global var.
// By encapsulating this here, this entire shim will process before subsequent imports.

import $ from 'jquery';
window.jQuery = window.$ = $;
export { $ };
