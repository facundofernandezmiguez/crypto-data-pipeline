#!/usr/bin/env python3
"""
Aplicación CLI para obtener datos de criptomonedas desde la API de CoinGecko.
"""
import os
import click
import logging
import datetime
from dateutil import parser
from dateutil.rrule import rrule, DAILY
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import json
from pathlib import Path

from crypto_app.coingecko_client import CoinGeckoAPI
from crypto_app.db import Database

# Configuración de logging
logger = logging.getLogger(__name__)

def setup_logging(log_level=logging.INFO):
    """
    Configurar el sistema de logging.
    
    Args:
        log_level: El nivel de logging (por defecto: INFO)
    """
    # Crear directorio de logs si no existe
    log_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs'))
    log_dir.mkdir(exist_ok=True)
    
    # Configurar logger principal
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Limpiar handlers existentes para evitar logs duplicados
    if logger.handlers:
        logger.handlers.clear()
    
    # Crear formateadores
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # Crear handler de archivo (rotativo para mantener el tamaño del archivo de logs manejable)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / 'crypto_app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    
    # Registrar mensaje inicial de configuración
    logging.info("Logging configured successfully")

@click.group()
def cli():
    """CLI para obtener datos de CoinGecko."""
    pass

@cli.command(name="get-history")
@click.option('--date', required=True, help='Date in ISO8601 format (YYYY-MM-DD)')
@click.option('--coin', required=True, help='Coin identifier (e.g., bitcoin)')
@click.option('--store-db', is_flag=True, help='Store data in PostgreSQL database')
def get_history(date, coin, store_db):
    """Obtener datos de una moneda para una fecha específica y guardarlos localmente."""
    setup_logging()
    logger.info("Fetching data for %s on %s", coin, date)
    
    try:
        # Analizar y validar la fecha
        parsed_date = parser.parse(date).date()
        formatted_date = parsed_date.strftime('%d-%m-%Y')
        
        logger.debug("Formatted date for API request: %s", formatted_date)
        
        # Initialize API client
        api = CoinGeckoAPI()
        
        # Fetch data
        data = api.get_coin_history(coin, formatted_date)
        
        # Store data in file system
        data_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', coin))
        data_dir.mkdir(exist_ok=True, parents=True)
        
        date_str = parsed_date.strftime('%Y-%m-%d')
        file_name = f"{coin}_{date_str}.json"
        file_path = data_dir / file_name
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("Data saved successfully to %s", file_path)
        click.echo(f"Data for {coin} on {date} saved to {file_path}")
        
        # If requested, store in database
        if store_db:
            try:
                db = Database()
                if not db.connect():
                    logger.error("Could not connect to database. Check connection settings.")
                    click.echo("Error: Could not connect to database.", err=True)
                    return
                
                # Initialize database if needed
                db.initialize_db()
                
                # Save data to database
                if db.save_coin_data(coin, parsed_date, data):
                    logger.info("Data saved to PostgreSQL database")
                    click.echo(f"Data for {coin} on {date} also saved to PostgreSQL database")
                else:
                    logger.error("Failed to save data to PostgreSQL database")
                    click.echo("Error: Failed to save to database", err=True)
            except Exception as e:
                logger.error("Database error: %s", str(e))
                click.echo(f"Database error: {str(e)}", err=True)
        
    except Exception as e:
        logger.error("Error fetching data: %s", str(e))
        click.echo(f"Error: {str(e)}", err=True)

@cli.command(name="bulk-process")
@click.option('--start-date', required=True, help='Start date in ISO8601 format (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date in ISO8601 format (YYYY-MM-DD)')
@click.option('--coin', required=True, help='Coin identifier (e.g., bitcoin)')
@click.option('--concurrent/--sequential', default=False, help='Run in concurrent mode')
@click.option('--max-workers', default=multiprocessing.cpu_count(), help='Maximum number of worker threads when running concurrently')
@click.option('--store-db', is_flag=True, help='Store data in PostgreSQL database')
def bulk_process(start_date, end_date, coin, concurrent, max_workers, store_db):
    """Obtener datos de una moneda para un rango de fechas."""
    setup_logging()
    logger.info("Bulk fetching data for %s from %s to %s", coin, start_date, end_date)
    
    try:
        # Analizar y validar las fechas
        start = parser.parse(start_date).date()
        end = parser.parse(end_date).date()
        
        if start > end:
            raise ValueError("Start date must be before end date")
        
        # Generar lista de fechas
        dates = [dt.date() for dt in rrule(DAILY, dtstart=start, until=end)]
        
        if concurrent:
            logger.info("Running in concurrent mode with %s workers", max_workers)
            _bulk_fetch_concurrent(coin, dates, max_workers, store_db)
        else:
            logger.info("Running in sequential mode")
            _bulk_fetch_sequential(coin, dates, store_db)
            
        logger.info("Bulk fetch completed for %s from %s to %s", coin, start_date, end_date)
        click.echo(f"Bulk fetch completed for {coin} from {start_date} to {end_date}")
        
    except Exception as e:
        logger.error("Error in bulk fetch: %s", str(e))
        click.echo(f"Error: {str(e)}", err=True)

def _process_single_date(coin, date, store_db=False):
    """Procesar una sola fecha para una moneda."""
    try:
        formatted_date = date.strftime('%d-%m-%Y')
        logger.info("Processing %s for %s", coin, formatted_date)
        
        # Initialize API client
        api = CoinGeckoAPI()
        
        # Fetch data
        data = api.get_coin_history(coin, formatted_date)
        
        # Store data in file system
        data_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', coin))
        data_dir.mkdir(exist_ok=True, parents=True)
        
        date_str = date.strftime('%Y-%m-%d')
        file_name = f"{coin}_{date_str}.json"
        file_path = data_dir / file_name
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("Data saved successfully to %s", file_path)
        
        # If requested, store in database
        if store_db:
            try:
                db = Database()
                if db.connect():
                    # Inicializar base de datos si es necesario
                    db.initialize_db()
                    
                    # Guardar datos en la base de datos
                    if db.save_coin_data(coin, date, data):
                        logger.info("Data saved to PostgreSQL database")
                    else:
                        logger.warning("Failed to save data to PostgreSQL database")
                else:
                    logger.error("Could not connect to database for %s on %s", coin, date)
            except Exception as e:
                logger.error("Database error for %s on %s: %s", coin, date, str(e))
        
        return True
    except Exception as e:
        logger.error("Error processing %s for %s: %s", coin, date, str(e))
        return False

def _bulk_fetch_sequential(coin, dates, store_db=False):
    """Obtener datos para un rango de fechas secuencialmente."""
    success_count = 0
    for date in tqdm(dates, desc=f"Obteniendo datos de {coin}"):
        if _process_single_date(coin, date, store_db):
            success_count += 1
    
    click.echo(f"Procesados con éxito {success_count} de {len(dates)} fechas para {coin}")

def _bulk_fetch_concurrent(coin, dates, max_workers, store_db=False):
    """Obtener datos para un rango de fechas concurrentemente."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Procesar fechas con ThreadPoolExecutor
        results = list(tqdm(
            executor.map(lambda date: _process_single_date(coin, date, store_db), dates),
            total=len(dates),
            desc=f"Obteniendo datos de {coin}"
        ))
    
    # Recopilar resultados
    success_count = results.count(True)
    click.echo(f"Procesados con éxito {success_count} de {len(dates)} fechas para {coin}")

if __name__ == '__main__':
    cli()
