import xarray as xr
import pandas as pd
import pytest
import numpy as np

import kerchunk.zarr
import kerchunk.utils


@pytest.fixture(scope="module")
def ds():
    ds = xr.Dataset(
        {
            "x": xr.DataArray(np.linspace(-np.pi, np.pi, 10), dims=["x"]),
            "y": xr.DataArray(np.linspace(-np.pi / 2, np.pi / 2, 10), dims=["y"]),
            "time": xr.DataArray(pd.date_range("2020", "2021"), dims=["time"]),
        },
    )
    ds["temp"] = (
        np.cos(ds.x)
        * np.sin(ds.y)
        * xr.ones_like(ds.time).astype("float")
        * np.random.random(ds.time.shape)
    )
    return ds


@pytest.fixture
def zarr_in_zip(tmpdir, ds):
    def _zip(file):
        import os
        import zipfile

        filename = file + os.path.extsep + "zip"
        with zipfile.ZipFile(
            filename, "w", compression=zipfile.ZIP_STORED, allowZip64=True
        ) as fh:
            for root, _, filenames in os.walk(file):
                for each_filename in filenames:
                    each_filename = os.path.join(root, each_filename)
                    fh.write(each_filename, os.path.relpath(each_filename, file))
        return filename

    fn = f"{tmpdir}/test.zarr"
    ds.to_zarr(fn, mode="w")
    return _zip(fn)


def test_zarr_in_zip(zarr_in_zip, ds):
    out = kerchunk.zarr.ZarrToZarr(
        url="zip://", storage_options={"fo": zarr_in_zip}
    ).translate()
    ds2 = xr.open_dataset(
        "reference://",
        engine="zarr",
        backend_kwargs={
            "storage_options": {
                "fo": out,
                "remote_protocol": "zip",
                "remote_options": {"fo": zarr_in_zip},
            },
            "consolidated": False,
        },
    )
    assert ds.equals(ds2)
