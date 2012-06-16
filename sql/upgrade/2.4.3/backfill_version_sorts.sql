/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

UPDATE productdims SET version_sort = old_version_sort(version);

UPDATE product_versions SET version_sort = version_sort(release_version, beta_number);

ANALYZE productdims;
ANALYZE product_versions;