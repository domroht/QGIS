import os
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)

    # Rasterio / GDAL data
    gdal_data = bundle_dir / "rasterio" / "gdal_data"

    if gdal_data.is_dir():
        os.environ["GDAL_DATA"] = str(gdal_data)

    # Rasterio / PROJ data
    proj_data = bundle_dir / "rasterio" / "proj_data"

    if proj_data.is_dir():
        os.environ["PROJ_DATA"] = str(proj_data)

    # Some GDAL installations use PROJ_LIB instead of PROJ_DATA.
    if proj_data.is_dir():
        os.environ["PROJ_LIB"] = str(proj_data)