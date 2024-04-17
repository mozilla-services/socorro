# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from click.testing import CliRunner

from gcs_cli import gcs_group


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(gcs_group, ["--help"])
    assert result.exit_code == 0


def test_upload_file_to_root(gcs_helper, tmp_path):
    """Test whether the module loads and spits out help."""
    bucket = gcs_helper.create_bucket("test").name
    path = tmp_path / uuid4().hex
    path.write_text(path.name)
    result = CliRunner().invoke(
        gcs_group, ["upload", str(path.absolute()), f"gs://{bucket}"]
    )
    assert result.exit_code == 0
    assert gcs_helper.download(bucket, path.name) == path.name.encode("utf-8")


def test_upload_file_to_dir(gcs_helper, tmp_path):
    """Test whether the module loads and spits out help."""
    bucket = gcs_helper.create_bucket("test").name
    path = tmp_path / uuid4().hex
    path.write_text(path.name)
    result = CliRunner().invoke(
        gcs_group, ["upload", str(path.absolute()), f"gs://{bucket}/{path.name}/"]
    )
    assert result.exit_code == 0
    assert gcs_helper.download(bucket, f"{path.name}/{path.name}") == path.name.encode(
        "utf-8"
    )


def test_upload_dir_to_dir(gcs_helper, tmp_path):
    """Test whether the module loads and spits out help."""
    bucket = gcs_helper.create_bucket("test").name
    path = tmp_path / uuid4().hex
    path.write_text(path.name)
    result = CliRunner().invoke(
        gcs_group, ["upload", str(tmp_path.absolute()), f"gs://{bucket}/{path.name}"]
    )
    assert result.exit_code == 0
    assert gcs_helper.download(bucket, f"{path.name}/{path.name}") == path.name.encode(
        "utf-8"
    )
