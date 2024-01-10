## Calculando os Índices Vegetativos com Python

#### Passo 1
Instanciar a classe passando o usuário e senha para a conexão com a API Sentinel
```python
processor = VegetativeIndexProcessor(username, password)
```
#### Passo 2
Defina o arquivo que terá as coordenadas
```python
processor.set_file("nome_do_arquivo.geojson")
```
#### Passo 3
Defina as datas de início e fim, respectivamente
```python
processor.set_date("2023-09-01", "2023-10-01")
```
#### Passo 4
Defina a porcentagem máxima de nuvens
```python
processor.set_cloud(30)
```
#### Passo 5
Download e mask das imagens
```python
processor.download()
processor.mask_area()
```
#### Passo 6
Calculando os índices vegetativos
```python
ndvi = processor.calculate_ndvi()
msavi = processor.calculate_msavi()
```
O retorno de cada função é o indice calculado

#### Passo 7
Salvar e exibir a imagem calculada usando as funções e `plot`
```python
processor.plot(index=ndvi, name="ndvi")
```