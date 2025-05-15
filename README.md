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
├── crypto_app/                  # Módulos CLI y conexión a API/DB
│   ├── __init__.py
│   ├── cli.py                   # Punto de entrada con comandos: get-history, bulk-process, --store-db
│   ├── coingecko_client.py      # Lógica HTTP / análisis de JSON
│   └── db.py                    # Conexión SQLAlchemy, inserciones y upserts mensuales
│   └── daily_fetch.py           # Script para ejecución diaria programada
│
├── sql/                         # Consultas SQL
│   ├── create_tables.sql        # Creación de tablas DDL
│   └── analysis_queries.sql     # Consultas DQL para promedios mensuales y análisis de recuperación
│
├── analysis/                    # Scripts de análisis en Python
│   ├── feature_engineering.py   # Generación de características + exportación de CSV/gráficos
│   └── regression.py            # Entrenamiento/evaluación de modelos
│
├── notebooks/                   # Notebooks Jupyter para exploración interactiva
│   └── coin_analysis.ipynb
│
├── data/                        # Directorio de salida (JSONs, imágenes, CSVs)
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
Aclaración: debido a que esta es la versión free de la api, muchas veces se alcanza el rate limit. Tuve que reejecutar varias veces algunas fechas especificas para obtener todos los datos.

Los archivos json se encuentran en la carpeta /data.

## Variables de Entorno

Crea un archivo `.env` con las siguientes variables:

```
DATABASE_URL=postgresql://username:password@localhost:5432/crypto
COINGECKO_API_KEY=tu_api_key_si_está_disponible
```

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
   Deberías ver:

| Schema | Name | Type | Owner |
|--------|------|------|-------|
| public | coin_history | table | postgres |
| public | coin_monthly_aggregates | table | postgres |

### E3. Analysing coin data with SQL 👓

Para responder a las preguntas de la Sección 3, sigue estos pasos:

1. **Conectate a la base de datos PostgreSQL**
   ```bash
   docker-compose exec db psql -U postgres -d postgres
   ```

2. **Ejecutá las consultas SQL desde el archivo `analysis_queries.sql`**
   
   El archivo `analysis_queries.sql` contiene dos consultas principales para responder a las preguntas de la Sección 3:
   
   - **Query 1**: Calcula el precio promedio por mes para cada moneda
   - **Query 2**: Calcula el aumento después de caídas consecutivas de más de 3 días

   Podés copiar y pegar estas consultas desde el archivo, o ejecutar el archivo completo con:

   ```sql
   \i /docker-entrypoint-initdb.d/analysis_queries.sql
   ```

Consultá el archivo `sql/analysis_queries.sql` para ver la documentación detallada de las consultas.



```

Sigue las instrucciones para agregar la entrada necesaria a tu crontab.

## 4. Finance Meets Data Science

Navegar al directorio del proyecto e iniciar los contenedores

```
cd c:/Users/corebi/MLE Mutt/crypto-data-pipeline
docker-compose up -d
```

Ejecutá las notebooks de análisis exploratorio de datos y de predicción de precios