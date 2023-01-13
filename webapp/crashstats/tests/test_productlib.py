# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for productlib utilities and product_details files"""

import pytest

from crashstats.productlib import (
    get_product_files,
    validate_product_file,
)


@pytest.mark.parametrize("fn", get_product_files())
def test_product_details_files(fn):
    """Validate product files in product_details directory"""
    validate_product_file(fn)
