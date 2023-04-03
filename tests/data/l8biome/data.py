#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import hashlib
import os
import shutil
from typing import Dict, List, Union

import numpy as np
import rasterio
from rasterio import Affine
from rasterio.crs import CRS

SIZE = 36

np.random.seed(0)

FILENAME_HIERARCHY = Union[Dict[str, "FILENAME_HIERARCHY"], List[str]]

bands = [
    "B1.TIF",
    "B2.TIF",
    "B3.TIF",
    "B4.TIF",
    "B5.TIF",
    "B6.TIF",
    "B7.TIF",
    "B8.TIF",
    "B8A.TIF",
    "B9.TIF",
    "B10.TIF",
    "B11.TIF",
    "B12.TIF",
]

barren_prefix = "LC80420082013220LGN00"
forest_prefix = "LC80070662014234LGN00"

filenames: FILENAME_HIERARCHY = {
    "barren": {barren_prefix: []},
    "forest": {forest_prefix: []},
}

for band in bands:
    filenames["barren"][barren_prefix].append(f"{barren_prefix}_{band}")
    filenames["forest"][forest_prefix].append(f"{forest_prefix}_{band}")

filenames["barren"][barren_prefix].append(f"{barren_prefix}_fixedmask.img")
filenames["forest"][forest_prefix].append(f"{forest_prefix}_fixedmask.img")


def create_file(path: str) -> None:
    dtype = "uint16"
    profile = {
        "driver": "GTiff",
        "dtype": dtype,
        "width": SIZE,
        "height": SIZE,
        "count": 1,
        "crs": CRS.from_epsg(32615),
        "transform": Affine(30.0, 0.0, 339885.0, 0.0, -30.0, 8286915.0),
    }

    if path.endswith("B8.TIF"):
        profile["width"] = profile["height"] = SIZE * 2

    Z = np.random.randn(SIZE, SIZE).astype(profile["dtype"])

    if path.endswith("fixedmask.img"):
        Z = np.random.randint(4, size=(SIZE, SIZE), dtype=dtype)

    with rasterio.open(path, "w", **profile) as src:
        src.write(Z, 1)


def create_directory(directory: str, hierarchy: FILENAME_HIERARCHY) -> None:
    if isinstance(hierarchy, dict):
        # Recursive case
        for key, value in hierarchy.items():
            path = os.path.join(directory, key)
            os.makedirs(path, exist_ok=True)
            create_directory(path, value)
    else:
        # Base case
        for value in hierarchy:
            path = os.path.join(directory, value)
            create_file(path)


if __name__ == "__main__":
    create_directory(".", filenames)

    directories = ["barren", "forest"]
    for directory in directories:
        filename = str(directory)

        # Create tarballs
        shutil.make_archive(filename, "gztar", ".", directory)

        # # Compute checksums
        with open(f"{filename}.tar.gz", "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
            print(filename, md5)
