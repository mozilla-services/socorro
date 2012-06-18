/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

BEGIN;

ALTER  TABLE "product_version_builds" DROP CONSTRAINT "product_version_builds_product_version_id_fkey" ;

ALTER  TABLE "product_version_builds" ADD CONSTRAINT "product_version_builds_product_version_id_fkey" FOREIGN KEY (product_version_id) REFERENCES product_versions(product_version_id) ON DELETE CASCADE;

COMMIT;

ALTER TABLE "signature_products" DROP CONSTRAINT "signature_products_product_version_id_fkey";

ALTER TABLE "tcbs" DROP CONSTRAINT "tcbs_product_version_id_fkey";