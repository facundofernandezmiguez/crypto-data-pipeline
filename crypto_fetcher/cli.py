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

from api import CoinGeckoAPI
from storage import DataStorage
from log_config import setup_logging

# Setup logging
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """CoinGecko data fetcher CLI."""
    pass

@cli.command()
@click.option('--date', required=True, help='Date in ISO8601 format (YYYY-MM-DD)')
@click.option('--coin', required=True, help='Coin identifier (e.g., bitcoin)')
def fetch(date, coin):
    """Fetch coin data for a specific date and store it locally."""
    setup_logging()
    logger.info(f"Fetching data for {coin} on {date}")
    
    try:
        # Parse and validate date
        parsed_date = parser.parse(date).date()
        formatted_date = parsed_date.strftime('%d-%m-%Y')
        
        logger.debug("Formatted date for API request: %s", formatted_date)
        
        # Initialize API client
        api = CoinGeckoAPI()
        
        # Fetch data
        data = api.get_coin_history(coin, formatted_date)
        
        # Store data
        storage = DataStorage()
        filename = storage.save_coin_data(coin, parsed_date, data)
        
        logger.info(f"Data saved successfully to {filename}")
        click.echo(f"Data for {coin} on {date} saved to {filename}")
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--start-date', required=True, help='Start date in ISO8601 format (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date in ISO8601 format (YYYY-MM-DD)')
@click.option('--coin', required=True, help='Coin identifier (e.g., bitcoin)')
@click.option('--concurrent/--sequential', default=False, help='Run in concurrent mode')
@click.option('--max-workers', default=multiprocessing.cpu_count(), help='Maximum number of worker threads when running concurrently')
def bulk_fetch(start_date, end_date, coin, concurrent, max_workers):
    """Fetch coin data for a range of dates."""
    setup_logging()
    logger.info(f"Bulk fetching data for {coin} from {start_date} to {end_date}")
    
    try:
        # Parse and validate dates
        start = parser.parse(start_date).date()
        end = parser.parse(end_date).date()
        
        if start > end:
            raise ValueError("Start date must be before end date")
        
        # Generate list of dates
        dates = [dt.date() for dt in rrule(DAILY, dtstart=start, until=end)]
        
        if concurrent:
            logger.info(f"Running in concurrent mode with {max_workers} workers")
            _bulk_fetch_concurrent(coin, dates, max_workers)
        else:
            logger.info("Running in sequential mode")
            _bulk_fetch_sequential(coin, dates)
            
        logger.info(f"Bulk fetch completed for {coin} from {start_date} to {end_date}")
        click.echo(f"Bulk fetch completed for {coin} from {start_date} to {end_date}")
        
    except Exception as e:
        logger.error(f"Error in bulk fetch: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)

def _process_single_date(coin, date):
    """Process a single date for a coin."""
    try:
        formatted_date = date.strftime('%d-%m-%Y')
        logger.info(f"Processing {coin} for {formatted_date}")
        
        # Initialize API client
        api = CoinGeckoAPI()
        
        # Fetch data
        data = api.get_coin_history(coin, formatted_date)
        
        # Store data
        storage = DataStorage()
        filename = storage.save_coin_data(coin, date, data)
        
        logger.info(f"Data saved successfully to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error processing {coin} for {date}: {str(e)}")
        return False

def _bulk_fetch_sequential(coin, dates):
    """Fetch data for a range of dates sequentially."""
    success_count = 0
    for date in tqdm(dates, desc=f"Fetching {coin} data"):
        if _process_single_date(coin, date):
            success_count += 1
    
    click.echo(f"Successfully processed {success_count} out of {len(dates)} dates for {coin}")

def _bulk_fetch_concurrent(coin, dates, max_workers):
    """Fetch data for a range of dates concurrently."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(
            executor.map(lambda date: _process_single_date(coin, date), dates),
            total=len(dates),
            desc=f"Fetching {coin} data"
        ))
    
    success_count = results.count(True)
    click.echo(f"Successfully processed {success_count} out of {len(dates)} dates for {coin}")

if __name__ == '__main__':
    cli()
