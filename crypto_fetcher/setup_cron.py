#!/usr/bin/env python3
"""
Script to set up CRON job for daily data collection.
"""
import os
import sys
import logging
from crontab import CronTab
from pathlib import Path

def setup_cron_job():
    """
    Set up a CRON job to run the CLI app every day at 3am
    for bitcoin, ethereum and cardano.
    """
    try:
        # Get absolute path to the CLI script
        script_dir = Path(__file__).resolve().parent
        cli_path = script_dir / 'cli.py'
        
        # Use python executable from current environment
        python_path = sys.executable
        
        # Get the current user's crontab
        cron = CronTab(user=True)
        
        # Remove any existing jobs for our script to avoid duplicates
        for job in cron.find_comment('crypto_fetcher_daily'):
            cron.remove(job)
            print("Removed existing crypto_fetcher_daily job")
        
        # Set up jobs for each coin
        coins = ['bitcoin', 'ethereum', 'cardano']
        
        for coin in coins:
            # Create a new job
            job = cron.new(comment=f'crypto_fetcher_daily_{coin}')
            
            # Command to run
            # Use today's date in ISO format
            command = f'{python_path} {cli_path} fetch --date $(date +\\%Y-\\%m-\\%d) --coin {coin}'
            
            # Set the command and timing (3am daily)
            job.setall('0 3 * * *')
            job.set_command(command)
            
            print(f"Added CRON job for {coin}")
        
        # Write the changes
        cron.write()
        print("CRON jobs set up successfully")
        
        # Display the actual crontab entries
        print("\nCurrent CRON jobs:")
        for job in cron:
            print(job)
            
    except Exception as e:
        print(f"Error setting up CRON job: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    setup_cron_job()
