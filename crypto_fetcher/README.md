# Crypto Fetcher CLI

Una aplicación CLI en Python para obtener y almacenar datos históricos de criptomonedas desde la API de CoinGecko.

## Requisitos

- Python 3.7+
- API key de CoinGecko (ya configurada: 'CG-E61ywJ7ucHsXH96nDttVtmcG')

## Instalación

1. Clona o descarga este repositorio
2. Instala las dependencias requeridas:

```bash
pip install -r requirements.txt
```

## Configuración

La aplicación utiliza por defecto la API key proporcionada. Si deseas cambiarla, puedes:

1. Modificar el valor en el archivo `api.py`
2. O establecer la variable de entorno `COINGECKO_API_KEY`

## Uso

### Obtener datos para una fecha específica

```bash
python cli.py fetch --date 2023-01-01 --coin bitcoin
```

Parámetros:
- `--date`: Fecha en formato ISO8601 (AAAA-MM-DD)
- `--coin`: Identificador de la criptomoneda (ej: bitcoin, ethereum, cardano)

### Obtener datos para un rango de fechas

```bash
python cli.py bulk-fetch --start-date 2023-01-01 --end-date 2023-01-31 --coin bitcoin
```

Parámetros:
- `--start-date`: Fecha de inicio en formato ISO8601 (AAAA-MM-DD)
- `--end-date`: Fecha final en formato ISO8601 (AAAA-MM-DD)
- `--coin`: Identificador de la criptomoneda
- `--concurrent/--sequential`: Ejecutar en modo concurrente o secuencial (por defecto: secuencial)
- `--max-workers`: Número máximo de workers para ejecuciones concurrentes (por defecto: número de CPU cores)

Ejemplo con procesamiento concurrente:
```bash
python cli.py bulk-fetch --start-date 2023-01-01 --end-date 2023-01-31 --coin bitcoin --concurrent --max-workers 4
```

## Configuración CRON

La aplicación incluye un script para configurar automáticamente tareas CRON que ejecutarán la aplicación diariamente a las 3 AM para bitcoin, ethereum y cardano:

```bash
python setup_cron.py
```

Este script:

1. Establece una tarea CRON para ejecutar `cli.py fetch` cada día a las 3 AM para cada una de las tres criptomonedas
2. Remueve cualquier tarea existente con el mismo comentario para evitar duplicados
3. Utiliza la fecha actual para cada ejecución

Los trabajos CRON configurados serán:

```
# Para bitcoin
0 3 * * * /ruta/al/python /ruta/al/cli.py fetch --date $(date +\%Y-\%m-\%d) --coin bitcoin

# Para ethereum
0 3 * * * /ruta/al/python /ruta/al/cli.py fetch --date $(date +\%Y-\%m-\%d) --coin ethereum

# Para cardano
0 3 * * * /ruta/al/python /ruta/al/cli.py fetch --date $(date +\%Y-\%m-\%d) --coin cardano
```

> **Nota**: En sistemas Windows, puedes usar el Programador de tareas como alternativa a CRON.

## Estructura de Datos

Los datos se almacenan en formato JSON en la siguiente estructura:

```
data/
  ├── bitcoin/
  │     ├── bitcoin_2023-01-01.json
  │     └── ...
  ├── ethereum/
  │     ├── ethereum_2023-01-01.json
  │     └── ...
  └── cardano/
        ├── cardano_2023-01-01.json
        └── ...
```

## Logs

La aplicación mantiene logs tanto en consola como en archivos. Los archivos de log se encuentran en:

```
logs/crypto_fetcher.log
```

Los logs utilizan un sistema de rotación para mantener un tamaño manejable (máximo 10MB por archivo, con hasta 5 archivos de respaldo).

## Extensiones Futuras

- Implementar almacenamiento en base de datos SQL
- Añadir dashboard para visualización de datos
- Soporte para más endpoints de la API de CoinGecko
