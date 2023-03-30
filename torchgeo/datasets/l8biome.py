# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""L8Biome dataset."""

import glob
import os
from typing import Any, Callable, Dict, List, Optional, cast

from rasterio.crs import CRS

from .geo import RasterDataset
from .utils import BoundingBox, download_url, extract_archive


class L8Biome(RasterDataset):
    r"""L8 Biome datasets.

    The `L8 Biome <https://landsat.usgs.gov/landsat-8-cloud-cover-assessment-validation-data>`__ dataset
    is a cloud validation dataset of Pre-Collection Landsat 8 Operational Land Imager (OLI) Thermal Infrared Sensor (TIRS) terrain-corrected (Level-1T) scenes.

    Dataset features:
    * images evenly divided between eight unique biomes
    * 5 cloud cover categories

    Dataset format:

    * Each cloud mask is in ENVI binary format.
    Includes all bands from the original Landsat Level-1 data product (GeoTIFF), and its associated Level-1 metadata (MTL.txt file)

    If you use this dataset in your research, please cite the following:

    * https://doi.org/10.5066/F7251GDH
    * https://doi.org/10.1016/j.rse.2017.03.026

    .. versionadded:: 0.5
    """

    url = "https://huggingface.co/datasets/torchgeo/l8biome/blob/main/{}.tar.gz"
    # redistributed from https://landsat.usgs.gov/landsat-8-cloud-cover-assessment-validation-data

    filenames_to_md5 = {
        "barren": "bb446fda3f6af50930849bb135e99f9c",
        "forest": "21505d878abac830890ea84abddc3c46",
        "grass_crops": "33d0c553357f5a439aa85a45916ac89a",
        "shrubland": "f19afc6dfa818ee3868e7040441d4c6d",
        "snow_ice": "d7b56084e6267ee114419efdc7f664c9",
        "urban": "b5f6aabbb380e108c408a8ea5dae3835",
        "water": "d143049ef64e6e681cea380dd84680e9",
        "wetlands": "bff0d51db84e26a2a8e776c83ab2d331",
    }

    cmap = {
        0: (0, 0, 0, 0),
        1: (97, 74, 74, 255),
        2: (38, 115, 0, 255),
        3: (0, 197, 255, 255),
        4: (207, 207, 207, 255),
    }

    filename_glob = "LC*_B2.TIF"
    targz_file_glob = "*.tar.gz"

    def __init__(
        self,
        root: str = "data",
        crs: Optional[CRS] = None,
        res: Optional[float] = None,
        transforms: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        cache: bool = True,
        download: bool = False,
        checksum: bool = False,
    ) -> None:
        """Initialize a new L8Biome dataset instance.

        Args:
            root: root directory where dataset can be found
            transforms: a function/transform that takes input sample and its target as
                entry and returns a transformed version
            cache: if True, cache file handle to speed up repeated sampling
            res: resolution of the dataset in units of CRS
                (defaults to the resolution of the first file found)
            transforms: a function/transform that takes an input sample
                and returns a transformed version
            cache: if True, cache file handle to speed up repeated sampling
            download: if True, download dataset and store it in the root directory
            checksum: if True, check the MD5 after downloading files (may be slow)

        Raises:
            RuntimeError: if ``download=False`` and data is not found, or checksums
                don't match
        """
        self.root = root
        self.download = download
        self.checksum = checksum

        self._verify()

        super().__init__(root, crs=crs, res=res, transforms=transforms, cache=cache)

    def _verify(self) -> None:
        """Verify the integrity of the dataset.

        Raises:
            RuntimeError: if ``download=False`` but dataset is missing or checksum fails
        """
        # Check if the extracted files already exist
        pathname = os.path.join(self.root, "**", self.filename_glob)
        for fname in glob.iglob(pathname, recursive=True):
            if not fname.endswith(".tar.gz"):
                return

        # Check if the tar.gz files have already been downloaded
        pathname = os.path.join(self.root, self.targz_file_glob)
        if glob.glob(pathname):
            self._extract()
            return

        # Check if the user requested to download the dataset
        if not self.download:
            raise RuntimeError(
                f"Dataset not found in `root={self.root}` and `download=False`, "
                "either specify a different `root` directory or use `download=True` "
                "to automatically download the dataset."
            )

        # Download the dataset
        self._download()
        self._extract()

    def _download(self) -> None:
        """Download the dataset."""
        for biome, md5 in self.filenames_to_md5.items():
            download_url(
                self.url.format(biome), self.root, md5=md5 if self.checksum else None
            )

    def _extract(self) -> None:
        """Extract the dataset."""
        pathname = os.path.join(self.root, self.targz_file_glob)
        for tarfile in glob.iglob(pathname):
            extract_archive(tarfile)

    def __getitem__(self, query: BoundingBox) -> Dict[str, Any]:
        """Retrieve image/mask and metadata indexed by query.
        
        Args:
            query: (minx, maxx, miny, maxy, mint, maxt) coordinates to index
        Returns:
            sample of image, mask and metadata at that index

        Raises:
            IndexError: if query is not found in the index
        """
        hits = self.index.intersection(tuple(query), objects=True)
        img_filepaths = cast(List[str], [hit.object for hit in hits])
        mask_filepaths = [path.replace("images", "masks") for path in img_filepaths]

        if not img_filepaths:
            raise IndexError(
                f"query: {query} not found in index with bounds: {self.bounds}"
            )

        img = self._merge_files(img_filepaths, query, self.band_indexes)
        mask = self._merge_files(mask_filepaths, query, self.band_indexes)
        sample = {
            "crs": self.crs,
            "bbox": query,
            "image": img.float(),
            "mask": mask.long(),
        }

        if self.transforms is not None:
            sample = self.transforms(sample)

        return sample

    # Plotting code added as placeholder for now till I get it working.
    # Using LandCoverAI plotting as reference.

    # def plot(
    #     self,
    #     sample: Dict[str, Tensor],
    #     show_titles: bool = True,
    #     suptitle: Optional[str] = None,
    # ) -> plt.Figure:
    #     """Plot a sample from the dataset.

    #     Args:
    #         sample: a sample returned by :meth:`__getitem__`
    #         show_titles: flag indicating whether to show titles above each panel
    #         suptitle: optional string to use as a suptitle

    #     Returns:
    #         a matplotlib Figure with the rendered sample
    #     """
    #     image = np.rollaxis(sample["image"].numpy().astype("uint8").squeeze(), 0, 3)
    #     mask = sample["mask"].numpy().astype("uint8").squeeze()

    #     num_panels = 2
    #     showing_predictions = "prediction" in sample
    #     if showing_predictions:
    #         predictions = sample["prediction"].numpy()
    #         num_panels += 1

    #     fig, axs = plt.subplots(1, num_panels, figsize=(num_panels * 4, 5))
    #     axs[0].imshow(image)
    #     axs[0].axis("off")
    #     axs[1].imshow(mask, vmin=0, vmax=4, cmap=self.cmap, interpolation="none")
    #     axs[1].axis("off")
    #     if show_titles:
    #         axs[0].set_title("Image")
    #         axs[1].set_title("Mask")

    #     if showing_predictions:
    #         axs[2].imshow(
    #             predictions, vmin=0, vmax=4, cmap=self.cmap, interpolation="none"
    #         )
    #         axs[2].axis("off")
    #         if show_titles:
    #             axs[2].set_title("Predictions")

    #     if suptitle is not None:
    #         plt.suptitle(suptitle)
    #     return fig
