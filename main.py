from datetime import date

if __name__ == "__main__":
    ndvi_processor = Ndvi(
        "teste@teste.com",
        "file.geojson",
        date(2023, 7, 1),
        date.today(),
        0,
    )
    ndvi_processor()
