from cbers4asat import Cbers4aAPI  ##############################
import glob
from rasterio.warp import transform_geom
from shapely.geometry import Polygon

# import matplotlib.pyplot as plt
from rasterio.mask import mask

# from dotenv import load_dotenv
from datetime import datetime
from rasterio import plot
import numpy as np
import rasterio
import pyproj
import shutil
import json
import math
import glob
import sys
import os
from indexProcessing import Ndvi
from datetime import date


class VegetativeIndexProcessor:
    def __init__(self, username):
        print("-> Configurando a API")
        self.api = Cbers4aAPI(username)  ##############################

    def set_date(self, start_date, end_date):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")

    def set_file(self, file):
        self.file = file

    def set_cloud(self, value):
        self.cloud = int(value)

    def download(self):
        with open(self.file) as file:
            data = json.load(file)

        # Inicialize os valores mínimos e máximos para longitude e latitude
        min_lon = min_lat = float("inf")
        max_lon = max_lat = float("-inf")

        # Percorra as features do arquivo GeoJSON para encontrar os limites das coordenadas
        for feature in data["features"]:
            geometry = feature["geometry"]
            if geometry["type"] == "Polygon":
                coords = geometry["coordinates"][
                    0
                ]  # Pegue as coordenadas do polígono principal
                for coord in coords:
                    min_lon = min(min_lon, coord[0])
                    min_lat = min(min_lat, coord[1])
                    max_lon = max(max_lon, coord[0])
                    max_lat = max(max_lat, coord[1])

        # Crie a Bounding Box no formato desejado [-min_lon, -min_lat, -max_lon, -max_lat]
        bbox = [min_lon, min_lat, max_lon, max_lat]

        # Inicialize uma lista vazia para armazenar as coordenadas do polígono
        coords = []

        # Percorra as features do arquivo GeoJSON para extrair as coordenadas do polígono
        for feature in data["features"]:
            geometry = feature["geometry"]
            if geometry["type"] == "Polygon":
                coords.extend(
                    geometry["coordinates"][0]
                )  # Adicione as coordenadas do polígono principal

        # Crie um objeto Polygon usando as coordenadas coletadas
        polygon = Polygon(coords)

        # Agora você pode atribuir esse objeto Polygon a um atributo da sua classe
        self.polygon = polygon

        products = self.api.query(
            location=bbox,
            initial_date=self.start_date,
            end_date=self.end_date,
            cloud=self.cloud,
            limit=500,
        )

        gdf = self.api.to_geodataframe(products)
        self.api.download(
            products=gdf, bands=["red", "nir"], outdir="./downloads_3", with_folder=True
        )

        # Utilize glob para listar pastas dentro de ./downloads_3
        folders = glob.glob("./downloads_3/*/")

        self.band_03_files = []
        self.band_04_files = []

        # Itera sobre as pastas encontradas
        for folder in folders:
            # Utilize glob novamente para listar todos os arquivos .TIF dentro de cada pasta
            tif_files = glob.glob(os.path.join(folder, "*.tif"))

            # Itera sobre os arquivos .TIF
            for tif_file in tif_files:
                # Verifica se o nome do arquivo contém a substring "BAND"
                if "_BAND3" in tif_file:
                    self.band_03_files.append(tif_file)
                elif "_BAND4" in tif_file:
                    self.band_04_files.append(tif_file)

        ##Printando
        print("Arquivos da Banda 3:")
        for file in self.band_03_files:
            print(file)

        print("\nArquivos da Banda 4:")
        for file in self.band_04_files:
            print(file)


if __name__ == "__main__":
    ndvi_processor = Ndvi("teste", "file.geojson", date.today(), date.today(), 100)
    ndvi_processor()
