# Pipeline de Datos de Criptomonedas

Un pipeline completo para la obtención, almacenamiento y análisis de datos de precios de criptomonedas.

## Descripción General del Proyecto

Este proyecto proporciona un flujo de trabajo completo para:
1. Obtener datos históricos de criptomonedas desde la API de CoinGecko
2. Almacenar datos en una base de datos PostgreSQL
3. Analizar tendencias y patrones de precios
4. Construir y evaluar modelos predictivos

## Estructura del Proyecto

```
crypto-data-pipeline/
├── crypto_app/                  # Ej 1
│   ├── __init__.py
│   ├── cli.py                   # Punto de entrada con comandos: get-history, bulk-process, --store-db
│   ├── coingecko_client.py      # Lógica HTTP / análisis de JSON
│   └── db.py                    # Conexión SQLAlchemy, inserciones y upserts mensuales
│   └── daily_fetch.py           # Script para ejecución diaria programada
│
├── sql/                         # Consultas SQL
│   ├── create_tables.sql        # Creación de tablas  (Ej 2)
│   └── analysis_queries.sql     # Queries (Ej 3)
│
├── analysis/                    # Scripts de análisis en Python
│   ├── feature_engineering.py   # Generación de características + exportación de CSV/gráficos
│   └── regression.py            # Entrenamiento/evaluación de modelos
│
├── notebooks/                   # Notebooks Jupyter - ejercicio 4
│   └── EDA.ipynb                # 4.1 y 4.2
│   └── transform_data.ipynb     # 4.3
│   └── models.ipynb             # 4.4
│
├── data/                        # Directorio de salida (JSONs, gráficos, CSVs)
│
├── logs/                        # Archivos de registro de la aplicación
│
├── Dockerfile                   # Imagen Python de la aplicación
├── docker-compose.yml           # Orquesta la app + PostgreSQL con montaje de datos
├── requirements.txt             # Dependencias del proyecto
├── .gitignore                   # Reglas de ignorar en Git
└── README.md                    # Documentación del proyecto
```

## Instalación usando Docker 

1. Asegúrate de tener Docker y Docker Compose instalados en tu sistema.

2. Clona el repositorio:
   ```
   git clone https://github.com/facundofernandezmiguez/crypto-data-pipeline.git
   cd crypto-data-pipeline
   ```

3. Inicia los servicios:
   ```
   docker-compose up -d
   ```

Esto iniciará tanto la aplicación Python como la base de datos PostgreSQL.

## 1. Getting crypto token data 💸

### Interfaz de Línea de Comandos

La CLI proporciona varios comandos para la obtención y procesamiento de datos:

#### Obtener una fecha específica.

```
python -m crypto_app.cli get-history --coin bitcoin --date 2025-01-01
```

Si también quieres almacenar los datos en la base de datos:

```
python -m crypto_app.cli get-history --coin bitcoin --date 2025-01-01 --store-db
```

#### Procesamiento diario automatizado
La aplicación incluye funcionalidad para ejecutarse automáticamente cada día a las 3:00 AM y obtener datos para bitcoin, ethereum y cardano.

Para ejecutar la obtención diaria de datos para bitcoin, ethereum y cardano:

```
python -m crypto_app.daily_fetch
```

Para ver las instrucciones de configuración de tareas programadas:

```
python -m crypto_app.daily_fetch --setup
```

#### Procesamiento en lote para un rango de fechas

Para procesar un rango de fechas de forma secuencial:

```
python -m crypto_app.cli bulk-process --coin bitcoin --start-date 2023-01-01 --end-date 2023-01-31
```

Para procesamiento concurrente (más rápido):

```
python -m crypto_app.cli bulk-process --coin bitcoin --start-date 2023-01-01 --end-date 2023-01-31 --concurrent
```

Para almacenar también en la base de datos:

```
python -m crypto_app.cli bulk-process --coin bitcoin --start-date 2023-01-01 --end-date 2023-01-31 --store-db
```
Si corriste antes una fecha pero no la almacenaste en la base de datos, no hace falta volver a correrla. Podés ejecutar el código 
```bash
   python load_data.py
   ```
Este script busca todos los archivos JSON en la carpeta `data/` y los carga en la tabla `coin_history`.
   

## Ejemplos de Ejecución con Docker

Para ejecutar comandos específicos usando Docker:

```
docker-compose run app get-history --coin bitcoin --date 2025-01-01 --store-db
```

Para el procesamiento en lote con Docker:

```
docker-compose run app bulk-process --coin bitcoin --start-date 2025-01-01 --end-date 2025-05-13 --store-db

docker-compose run app bulk-process --coin ethereum --start-date 2025-01-01 --end-date 2025-05-13 --store-db

docker-compose run app bulk-process --coin cardano --start-date 2025-01-01 --end-date 2025-05-13 --store-db
```
Aclaración: debido a que esta es la versión free de la api de CoinGecko, muchas veces se alcanza el rate limit y algunas fechas no se cargan correctamente. Hay que reejecutar varias veces algunas fechas especificas para obtener todos los datos.

Los archivos json se encuentran en la carpeta /data.

## 2. Loading data into the database

### 🛠️ Creación de tablas en PostgreSQL

Para inicializar la base de datos con las tablas necesarias (coin_history y coin_monthly_aggregates), sigue estos pasos:

1. **Asegurate de estar en el directorio del proyecto**
   ```bash
   cd crypto-data-pipeline
   ```

2. **Verificar que el archivo SQL existe**
   ```bash
   dir sql/create_tables.sql
   ```

3. **Copiar el archivo al contenedor de PostgreSQL**
   ```bash
   docker cp sql/create_tables.sql crypto-data-pipeline-db-1:/create_tables.sql
   ```
   Asegúrate de reemplazar el nombre del contenedor si usas uno distinto.

4. **Ejecutar el script SQL en la base de datos**
   ```bash
   docker exec -it crypto-data-pipeline-db-1 psql -U postgres -d postgres -f /create_tables.sql
   ```
   Deberías ver mensajes como CREATE TABLE, CREATE INDEX, y COMMENT, indicando que las tablas fueron creadas exitosamente.

5. **Verificar que las tablas fueron creadas**
   ```bash
   docker exec -it crypto-data-pipeline-db-1 psql -U postgres -d postgres
   ```
   Y dentro del shell de PostgreSQL, ejecuta:
   ```sql
   \dt
   ```
   Deberías ver algo así:

| Schema | Name | Type | Owner |
|--------|------|------|-------|
| public | coin_history | table | postgres |
| public | coin_monthly_aggregates | table | postgres |

## 3. Analysing coin data with SQL 👓

Para responder a las preguntas de la Sección 3, sigue estos pasos:

1. **Conectate a la base de datos PostgreSQL**
   ```bash
   docker-compose exec db psql -U postgres -d postgres
   ```

2. **Ejecutá las consultas SQL desde el archivo `analysis_queries.sql`**
   
   El archivo `analysis_queries.sql` contiene dos consultas principales para responder a las preguntas de la Sección 3:
   
   - **Query 1**: Calcula el precio promedio por mes para cada moneda

   Deberías ver un resultado similar a este (dependiendo de qué meses y monedas hayas guardado): 
   
   | coin_id  | year | month | avg_price_usd |
   |----------|------|-------|---------------|
   | bitcoin  | 2024 | 9     | 60210.03      |
   | bitcoin  | 2024 | 10    | 65430.60      |
   | bitcoin  | 2024 | 11    | 88277.57      |
   | bitcoin  | 2024 | 12    | 98262.05      |
   | bitcoin  | 2025 | 1     | 99696.06      |
   | bitcoin  | 2025 | 2     | 95922.85      |
   | bitcoin  | 2025 | 3     | 85590.72      |
   | bitcoin  | 2025 | 4     | 86068.13      |
   | bitcoin  | 2025 | 5     | 99940.71      |
   | cardano  | 2024 | 9     | 0.35          |
   | cardano  | 2024 | 10    | 0.35          |
   | cardano  | 2024 | 11    | 0.67          |
   | cardano  | 2024 | 12    | 1.03          |
   | cardano  | 2025 | 1     | 0.99          |
   | cardano  | 2025 | 2     | 0.76          |
   | cardano  | 2025 | 3     | 0.74          |
   | cardano  | 2025 | 4     | 0.65          |
   | cardano  | 2025 | 5     | 0.74          |
   | ethereum | 2024 | 9     | 2464.41       |
   | ethereum | 2024 | 10    | 2520.05       |
   | ethereum | 2024 | 11    | 3077.43       |
   | ethereum | 2024 | 12    | 3655.90       |
   | ethereum | 2025 | 1     | 3329.32       |
   | ethereum | 2025 | 2     | 2715.39       |
   | ethereum | 2025 | 3     | 2043.64       |
   | ethereum | 2025 | 4     | 1687.62       |
   | ethereum | 2025 | 5     | 2131.09       |

   - **Query 2**: Calcula el aumento después de caídas consecutivas de más de 3 días
   
   Deberías ver este resultado: 
   
   | coin_id  | avg_price_increase_pct | current_market_cap_usd |
   |----------|------------------------|-----------------------|
   | ethereum | 26.97                  | 314.02B                |
   | cardano  | 109.95                 | 28.79B                 |
   | bitcoin  | 35.30                  | 2.06T                  |

   Podés copiar y pegar estas consultas desde el archivo, o ejecutar el archivo completo con:

   ```sql
   \i /docker-entrypoint-initdb.d/analysis_queries.sql
   ```

Consultá el archivo `sql/analysis_queries.sql` para ver la documentación detallada de las consultas.

## 4. Finance Meets Data Science


Ejecutá las notebooks de análisis exploratorio de datos y de predicción de precios. Se encuentran en la carpeta notebooks.

Recordá que debés iniciar Docker y ejecutar `docker-compose up -d` para iniciar los servicios y cargar la base de PostgreSQL.

Las respuestas a las consignas 4.1 y 4.2 se encuentran en la notebook `EDA.ipynb`;
4.3 se encuentra en la notebook `transform_data.ipynb` y 4.4 se encuentra en la notebook `models.ipynb`. Los outputs se encuentran en la carpeta `data`.

Se compararon 4 modelos de regresión:
- Regresión Lineal Multiple
- Ridge
- Lasso
- XGBoostRegressor.

De los modelos evaluados, Ridge Regression mostró el mejor desempeño general para predecir el precio del día siguiente en la mayoría de las criptomonedas, combinando buena precisión con estabilidad. Si bien XGBoost suele destacarse en tareas complejas, en este caso no superó a los modelos lineales, probablemente debido al tamaño y la naturaleza temporal del dataset.



