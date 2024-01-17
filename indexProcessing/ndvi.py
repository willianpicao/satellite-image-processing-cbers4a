import rasterio as rio
import numpy as np
from cbers4asat import Cbers4aAPI
from shapely.geometry import Polygon
from geojson import loads
from datetime import date
from glob import glob
from os.path import join


class Ndvi:
    def __init__(
        self,
        username: str,
        geojson_path: str,
        start_date: date,
        end_date: date,
        cloud_cover: int,
    ):
        self._api = Cbers4aAPI(username)
        self._username = username
        self._start_date = start_date
        self._end_date = end_date
        self._cloud_cover = cloud_cover

        with open(geojson_path, "r") as geojson:
            self._geojson = loads(geojson.read())

    def __call__(self):
        search_areas = []
        for feat in self._geojson.get("features"):
            (polygon_vertex,) = feat.get("geometry").get("coordinates")
            search_areas.append(Polygon(polygon_vertex))

        for search_area in search_areas:
            products = self._api.query(
                location=search_area,
                initial_date=self._start_date,
                end_date=self._end_date,
                cloud=self._cloud_cover,
                limit=1000,
                collections=["CBERS4A_WPM_L4_DN", "CBERS4A_WPM_L2_DN"],
            )

            if len(products.get("features")) > 0:
                self._api.download(
                    products=products,
                    bands=["red", "nir"],
                    outdir="downloads",
                    with_folder=True,
                )

                for folder in glob("downloads/*"):
                    red_file, nir_file = "", ""
                    for band in glob(join(folder, "*.tif")):
                        if "BAND3" in band:
                            red_file = band
                        elif "BAND4" in band:
                            nir_file = band

                    red_ds = rio.open(red_file)
                    nir_ds = rio.open(nir_file)

                    red_matrix = red_ds.read()
                    nir_matrix = nir_ds.read()

                    # Ignorar erro de divisão por zero
                    np.seterr(divide="ignore", invalid="ignore")

                    ndvi = (nir_matrix - red_matrix) / (nir_matrix + red_matrix)

                    out_meta = red_ds.meta.copy()

                    out_meta.update(dtype="float64")

                    with rio.open(join(folder, "ndvi.tif"), "w", **out_meta) as dst:
                        dst.write(ndvi)
            else:
                print(
                    f"Nenhuma imagem encontrada entre a data de {self._start_date} - {self._end_date}"
                )
