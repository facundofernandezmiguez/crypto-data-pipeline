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

## Instalación

### Opción 1: Usando Docker (Recomendado)

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

### Opción 2: Instalación Manual

1. Clona el repositorio:
   ```
   git clone https://github.com/facundofernandezmiguez/crypto-data-pipeline.git
   cd crypto-data-pipeline
   ```

2. Crea y activa un entorno virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Configura PostgreSQL por separado e inicializa la base de datos:
   ```
   psql -U postgres -f sql/create_tables.sql
   ```

## Uso

### Interfaz de Línea de Comandos

La CLI proporciona varios comandos para la obtención y procesamiento de datos:

#### 1. Obtener datos para una fecha específica

```
python -m crypto_app.cli get-history --coin bitcoin --date 2025-01-01
```

Si también quieres almacenar los datos en la base de datos:

```
python -m crypto_app.cli get-history --coin bitcoin --date 2025-01-01 --store-db
```

#### 2. Procesamiento diario automatizado

Para ejecutar la obtención diaria de datos para bitcoin, ethereum y cardano:

```
python -m crypto_app.daily_fetch
```

Para ver las instrucciones de configuración de tareas programadas:

```
python -m crypto_app.daily_fetch --setup
```

#### 3. Procesamiento en lote para un rango de fechas

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

### Análisis de Datos

1. Ejecutar ingeniería de características:
   ```
   python -m analysis.feature_engineering
   ```

2. Entrenar y evaluar modelos:
   ```
   python -m analysis.regression
   ```

3. Para análisis interactivo, lanzar Jupyter Notebook:
   ```
   jupyter notebook notebooks/coin_analysis.ipynb
   ```

## Ejemplos de Ejecución con Docker

Para ejecutar comandos específicos usando Docker:

```
docker-compose run app get-history --coin bitcoin --date 2025-01-01 --store-db
```

Para el procesamiento en lote con Docker:

```
docker-compose run app bulk-process --coin bitcoin --start-date 2023-01-01 --end-date 2023-01-31 --store-db
```

## Variables de Entorno

Crea un archivo `.env` con las siguientes variables:

```
DATABASE_URL=postgresql://username:password@localhost:5432/crypto
COINGECKO_API_KEY=tu_api_key_si_está_disponible
```

## Ejecución Programada

La aplicación incluye funcionalidad para ejecutarse automáticamente cada día a las 3:00 AM y obtener datos para bitcoin, ethereum y cardano.

### Configuración en Windows

Ejecuta el siguiente comando para ver las instrucciones de configuración:

```
python -m crypto_app.daily_fetch --setup
```

Sigue las instrucciones proporcionadas para configurar el Programador de tareas de Windows.

### Configuración en Linux

En sistemas Linux, puedes configurar un trabajo cron ejecutando:

```
python -m crypto_app.daily_fetch --setup
```

Sigue las instrucciones para agregar la entrada necesaria a tu crontab.

## Licencia

[MIT](LICENSE)
