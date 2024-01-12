from cbers4asat import Cbers4aAPI
from shapely.geometry import Polygon
from geojson import loads
from datetime import date


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
                limit=1,
                collections=["CBERS4A_WPM_L4_DN"],
            )

            print(products)
