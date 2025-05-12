"""
Module for interacting with the CoinGecko API.
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# API Key from environment variable or hardcoded for development
API_KEY = os.environ.get('COINGECKO_API_KEY', 'CG-E61ywJ7ucHsXH96nDttVtmcG')

class CoinGeckoAPI:
    """Client for the CoinGecko API."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key=None):
        """
        Initialize the CoinGecko API client.
        
        Args:
            api_key (str, optional): API key for CoinGecko. Defaults to environment variable.
        """
        self.api_key = api_key or API_KEY
        self.session = requests.Session()
        # Add API key to headers
        self.session.headers.update({
            # La API gratuita usa 'x-cg-demo-api-key' como encabezado
            'x-cg-demo-api-key': self.api_key,
            'User-Agent': 'CryptoDataPipeline/1.0'
        })
    
    def get_coin_history(self, coin_id, date):
        """
        Get historical data for a specific coin on a specific date.
        
        Args:
            coin_id (str): The coin identifier (e.g., bitcoin)
            date (str): The date in DD-MM-YYYY format
            
        Returns:
            dict: The API response data
        """
        endpoint = f"{self.BASE_URL}/coins/{coin_id}/history"
        params = {'date': date}
        
        logger.debug("Requesting data from %s with params %s", endpoint, params)
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint, params=params)
                response.raise_for_status()
                
                logger.debug("API request succeeded with status code %s", response.status_code)
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning("Rate limit exceeded. Retrying after %s seconds.", retry_after)
                    time.sleep(retry_after)
                    continue
                
                # Log more detailed error information
                logger.error("HTTP error occurred: %s", e)
                try:
                    error_response = response.json()
                    logger.error("API error details: %s", error_response)
                except:
                    logger.error("Raw response content: %s", response.text)
                if attempt < max_retries - 1:
                    logger.info("Retrying in %s seconds (attempt %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error("Request error occurred: %s", e)
                if attempt < max_retries - 1:
                    logger.info("Retrying in %s seconds (attempt %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
        # If we get here, all retries failed
        raise requests.exceptions.RequestException("Failed to get data after multiple attempts")
    
    def get_coin_list(self):
        """
        Get list of all available coins.
        
        Returns:
            list: List of available coins with their IDs
        """
        endpoint = f"{self.BASE_URL}/coins/list"
        
        logger.debug("Requesting coin list from %s", endpoint)
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint)
                response.raise_for_status()
                
                logger.debug("API request succeeded with status code %s", response.status_code)
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                logger.error("HTTP error occurred: %s", e)
                if attempt < max_retries - 1:
                    logger.info("Retrying in %s seconds (attempt %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error("Request error occurred: %s", e)
                if attempt < max_retries - 1:
                    logger.info("Retrying in %s seconds (attempt %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
        # If we get here, all retries failed
        raise requests.exceptions.RequestException("Failed to get coin list after multiple attempts")
