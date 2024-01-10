from sentinelsat import SentinelAPI, geojson_to_wkt, make_path_filter
from rasterio.warp import transform_geom
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from rasterio.mask import mask
from dotenv import load_dotenv
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

load_dotenv()


class VegetativeIndexProcessor:
    def __init__(self, username, password):
        print("-> Configurando a API")
        self.api = SentinelAPI(username, password, timeout=None)#
        #Subsituir sentinelAPI- por outra opção de dowload.
        #Baixar as bandas certas correspondentes para os calculos.
        

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

        # Captura as coordenadas
        coords = data["features"][0]["geometry"]["coordinates"][0]

        # Converte para o padrão polygon
        self.polygon = Polygon(coords)

        footprint = geojson_to_wkt(self.polygon.__geo_interface__)

        products = self.api.query(
            footprint,
            date=(self.start_date, self.end_date),
            platformname="Sentinel-2",
            processinglevel="Level-2A",
            cloudcoverpercentage=(0, self.cloud),
        )

        products_gdf = self.api.to_geodataframe(products)
        products_gdf.to_file("dados.geojson", driver="GeoJSON")

        product_ids = list(products_gdf.index)

        path_filter_band_04 = make_path_filter(f"*_B04_10m.jp2")
        path_filter_band_08 = make_path_filter(f"*_B08_10m.jp2")

        print("-> Baixando as imagens")
        for idx in product_ids:
            try:
                self.api.download(idx, nodefilter=path_filter_band_04)
                self.api.download(idx, nodefilter=path_filter_band_08)
            except:
                print(f"--> Erro ao baixar imagem ({idx})")

    def mask_area(self):
        # Extrair as coordenadas do anel externo do polígono
        exterior_coords = self.polygon.exterior.coords

        self.epsilon = 0.00001

        root_dir = os.getcwd()
        self.band_04_files = []
        self.band_08_files = []

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if "_B04_10m.jp2" in filename:
                    self.band_04_files.append(os.path.join(dirpath, filename))
                elif "_B08_10m.jp2" in filename:
                    self.band_08_files.append(os.path.join(dirpath, filename))

        self.extract_dates()

        try:
            # Define o sistema de referência espacial da imagem raster
            with rasterio.open(self.band_04_files[0]) as src:
                dst_crs = src.crs
        except:
            print("--> Nenhuma imagem encontrada nesse período")
            print("--> Saindo...")
            sys.exit()

        # Define o sistema de referência espacial das coordenadas do polígono (WGS84)
        self.src_crs = pyproj.CRS.from_epsg(4326)

        # Transforma as coordenadas do polígono para o mesmo SRS da imagem raster
        transformed_coords = transform_geom(
            self.src_crs, dst_crs, {"type": "Polygon", "coordinates": [exterior_coords]}
        )

        red_crops = []
        nir_crops = []

        print("-> Cortando as imagens")
        for idx in range(len(self.band_04_files)):
            with rasterio.open(self.band_04_files[idx]) as red:
                with rasterio.open(self.band_08_files[idx]) as nir:
                    self.kwargs = red.meta.copy()

                    red_crop, self.red_transform = mask(
                        red,
                        [transformed_coords],
                        crop=True,
                    )
                    nir_crop, _ = mask(
                        nir,
                        [transformed_coords],
                        crop=True,
                    )

                    red_crops.append(red_crop)
                    nir_crops.append(nir_crop)

        self.bands = [red_crops, nir_crops]

    def calculate_ndvi(self):
        red, nir = self.bands
        ndvi = []
        for i in range(len(red)):
            ndvi.append((nir[i] - red[i]) / (nir[i] + red[i] + self.epsilon))

        return ndvi

    def calculate_msavi(self):
        red, nir = self.bands
        msavi = []
        for i in range(len(red)):
            msavi.append(
                (
                    2 * nir[i]
                    + 1
                    - np.sqrt((2 * nir[i] + 1) ** 2 - 8 * (nir[i] - red[i]))
                )
                / 2
            )

        return msavi

    def extract_dates(self):
        self.dates = []
        temp_band_04 = []
        temp_band_08 = []

        for file in self.band_04_files:
            partes = file.split("_")
            data_str = partes[2]
            data_formatada = datetime.strptime(data_str, "%Y%m%dT%H%M%S")

            if self.start_date <= data_formatada <= self.end_date:
                self.dates.append(data_formatada)
                temp_band_04.append(file)
                temp_band_08.append(self.band_08_files[len(temp_band_04) - 1])

        self.band_04_files = temp_band_04
        self.band_08_files = temp_band_08

        self.sort_dates()

    def sort_dates(self):
        # Cria uma lista de tuplas, onde cada tupla contém uma data e os arquivos correspondentes
        data_and_files = list(zip(self.dates, self.band_04_files, self.band_08_files))

        # Ordena a lista com base nas datas
        data_and_files.sort(key=lambda x: x[0])

        # Desagrupa os elementos novamente
        self.dates, self.band_04_files, self.band_08_files = zip(*data_and_files)

    def plot(self, *, index, name):
        name = name.upper()
        print(f"-> Exibindo os cálculos do {name}")
        qtd = len(index)

        maximo = np.max(index)

        if maximo > 100 or name == "MSAVI":
            minimo = np.min(index)
            index = [(x - minimo) / (maximo - minimo) for x in index]

        num_colunas = math.ceil(math.sqrt(qtd))
        num_linhas = math.ceil(qtd / num_colunas)

        # Criar os subplots
        fig, axs = plt.subplots(num_linhas, num_colunas, figsize=(10, 5))

        # Remover subplots extras (se houver)
        if qtd < num_linhas * num_colunas:
            for i in range(qtd, num_linhas * num_colunas):
                fig.delaxes(axs.flatten()[i])

        # Adicionar cada imagem ao subplot correspondente
        for i, ax in enumerate(axs.flatten()):
            if i < qtd:
                ax.imshow(index[i].squeeze(), cmap="viridis", vmax=0.72)
                ax.set_title(f"{name} {i+1} {self.dates[i]}")
            else:
                if ax in fig.axes:
                    fig.delaxes(ax)

        # Ajustar layout
        plt.tight_layout()

        # Exibir o gráfico
        plt.show()


if __name__ == "__main__":
    username = os.getenv("username")
    password = os.getenv("password")

    # Instanciando a classe VegetativeIndexProcessor passando as credenciais
    processor = VegetativeIndexProcessor(username, password)

    # Definindo o arquivo que contém as coordenadas
    processor.set_file("file.geojson")

    # Definindo as datas de início e fim, respectivamente
    processor.set_date("2023-01-15", "2023-03-15")

    # Definindo a porcentagem máxima de núvens
    processor.set_cloud(30)

    processor.download()
    processor.mask_area()

    # Cálculo do NDVI e MSAVI
    ndvi = processor.calculate_ndvi()
    msavi = processor.calculate_msavi()

    # Passar o nome corretamente
    processor.plot(index=ndvi, name="ndvi")
    processor.plot(index=msavi, name="msavi")
