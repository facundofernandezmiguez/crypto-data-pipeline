#!/usr/bin/env python3
"""
CLI application to fetch cryptocurrency data from CoinGecko API.
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

# Setup logging
logger = logging.getLogger(__name__)

def setup_logging(log_level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        log_level: The logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs'))
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicate logs
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # Create file handler (rotating to keep log file size manageable)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / 'crypto_app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    
    # Log initial setup message
    logging.info("Logging configured successfully")

@click.group()
def cli():
    """CoinGecko data fetcher CLI."""
    pass

@cli.command(name="get-history")
@click.option('--date', required=True, help='Date in ISO8601 format (YYYY-MM-DD)')
@click.option('--coin', required=True, help='Coin identifier (e.g., bitcoin)')
@click.option('--store-db', is_flag=True, help='Store data in PostgreSQL database')
def get_history(date, coin, store_db):
    """Fetch coin data for a specific date and store it locally."""
    setup_logging()
    logger.info("Fetching data for %s on %s", coin, date)
    
    try:
        # Parse and validate date
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
    """Fetch coin data for a range of dates."""
    setup_logging()
    logger.info("Bulk fetching data for %s from %s to %s", coin, start_date, end_date)
    
    try:
        # Parse and validate dates
        start = parser.parse(start_date).date()
        end = parser.parse(end_date).date()
        
        if start > end:
            raise ValueError("Start date must be before end date")
        
        # Generate list of dates
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
    """Process a single date for a coin."""
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
                    # Initialize database if needed
                    db.initialize_db()
                    
                    # Save data to database
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
    """Fetch data for a range of dates sequentially."""
    success_count = 0
    for date in tqdm(dates, desc=f"Fetching {coin} data"):
        if _process_single_date(coin, date, store_db):
            success_count += 1
    
    click.echo(f"Successfully processed {success_count} out of {len(dates)} dates for {coin}")

def _bulk_fetch_concurrent(coin, dates, max_workers, store_db=False):
    """Fetch data for a range of dates concurrently."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(
            executor.map(lambda date: _process_single_date(coin, date, store_db), dates),
            total=len(dates),
            desc=f"Fetching {coin} data"
        ))
    
    success_count = results.count(True)
    click.echo(f"Successfully processed {success_count} out of {len(dates)} dates for {coin}")

if __name__ == '__main__':
    cli()
