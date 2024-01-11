from cbers4asat import Cbers4aAPI
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

        with open(geojson_path, "r") as geojson:
            self._geojson = loads(geojson.read())

    def __call__(self):
        print(self._geojson)
