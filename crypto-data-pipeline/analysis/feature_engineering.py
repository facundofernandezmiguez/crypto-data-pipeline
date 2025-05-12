"""
Module for feature engineering on cryptocurrency data.
"""
import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from crypto_app.db import Database

# Setup logging
logger = logging.getLogger(__name__)

def setup_logging(log_level=logging.INFO):
    """Set up logging for analysis scripts."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'analysis.log'))
        ]
    )

class FeatureEngineering:
    """Class for feature engineering on cryptocurrency data."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize feature engineering.
        
        Args:
            output_dir (str, optional): Directory for storing outputs.
        """
        self.db = Database()
        self.output_dir = output_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'features')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Make plots directory
        self.plots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'plots')
        os.makedirs(self.plots_dir, exist_ok=True)
    
    def load_price_data(self, coin_id: str) -> pd.DataFrame:
        """
        Load price data for a coin from database.
        
        Args:
            coin_id (str): Coin ID
            
        Returns:
            DataFrame: Price data
        """
        if not self.db.connect():
            logger.error("Could not connect to database")
            return pd.DataFrame()
            
        try:
            with self.db.engine.connect() as conn:
                query = """
                SELECT 
                    coin_id, 
                    fetch_date, 
                    price_usd 
                FROM coin_history 
                WHERE coin_id = :coin_id 
                AND price_usd IS NOT NULL 
                ORDER BY fetch_date
                """
                df = pd.read_sql_query(query, conn, params={'coin_id': coin_id})
                
                # Convert date to datetime
                df['fetch_date'] = pd.to_datetime(df['fetch_date'])
                df.set_index('fetch_date', inplace=True)
                
                logger.info("Loaded %s rows for %s", len(df), coin_id)
                return df
        except Exception as e:
            logger.error("Error loading price data: %s", str(e))
            return pd.DataFrame()
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create time-based features.
        
        Args:
            df (DataFrame): Price data
            
        Returns:
            DataFrame: Data with time features
        """
        # Create copy to avoid modifying original data
        result = df.copy()
        
        # Extract time features
        result['dayofweek'] = result.index.dayofweek
        result['month'] = result.index.month
        result['quarter'] = result.index.quarter
        result['year'] = result.index.year
        
        # Weekend flag (0=weekday, 1=weekend)
        result['is_weekend'] = result['dayofweek'].apply(lambda x: 1 if x >= 5 else 0)
        
        logger.info("Added time features: dayofweek, month, quarter, year, is_weekend")
        return result
    
    def create_lagged_features(self, df: pd.DataFrame, lags: List[int] = [1, 7, 30]) -> pd.DataFrame:
        """
        Create lagged features.
        
        Args:
            df (DataFrame): Price data
            lags (list): List of lag periods
            
        Returns:
            DataFrame: Data with lagged features
        """
        # Create copy to avoid modifying original data
        result = df.copy()
        
        # Create lagged features
        for lag in lags:
            result[f'price_lag_{lag}'] = result['price_usd'].shift(lag)
            
        # Remove rows with NaN values (due to lag creation)
        result = result.dropna()
        
        logger.info("Added lagged features: %s", [f'price_lag_{lag}' for lag in lags])
        return result
    
    def create_rolling_features(self, df: pd.DataFrame, windows: List[int] = [7, 14, 30]) -> pd.DataFrame:
        """
        Create rolling window features.
        
        Args:
            df (DataFrame): Price data
            windows (list): List of window sizes
            
        Returns:
            DataFrame: Data with rolling features
        """
        # Create copy to avoid modifying original data
        result = df.copy()
        
        # Create rolling window features
        for window in windows:
            result[f'price_mean_{window}d'] = result['price_usd'].rolling(window=window).mean()
            result[f'price_std_{window}d'] = result['price_usd'].rolling(window=window).std()
            result[f'price_min_{window}d'] = result['price_usd'].rolling(window=window).min()
            result[f'price_max_{window}d'] = result['price_usd'].rolling(window=window).max()
            
        # Remove rows with NaN values (due to rolling window creation)
        result = result.dropna()
        
        logger.info("Added rolling features for windows: %s", windows)
        return result
    
    def create_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create technical indicators.
        
        Args:
            df (DataFrame): Price data
            
        Returns:
            DataFrame: Data with technical indicators
        """
        # Create copy to avoid modifying original data
        result = df.copy()
        
        # Relative Strength Index (RSI) - 14 days
        delta = result['price_usd'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        result['rsi_14'] = 100 - (100 / (1 + rs))
        
        # Moving Average Convergence Divergence (MACD)
        result['ema_12'] = result['price_usd'].ewm(span=12, adjust=False).mean()
        result['ema_26'] = result['price_usd'].ewm(span=26, adjust=False).mean()
        result['macd'] = result['ema_12'] - result['ema_26']
        result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
        result['macd_histogram'] = result['macd'] - result['macd_signal']
        
        # Bollinger Bands (20, 2)
        result['bb_middle'] = result['price_usd'].rolling(window=20).mean()
        result['bb_stddev'] = result['price_usd'].rolling(window=20).std()
        result['bb_upper'] = result['bb_middle'] + (result['bb_stddev'] * 2)
        result['bb_lower'] = result['bb_middle'] - (result['bb_stddev'] * 2)
        result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
        
        # Remove rows with NaN values
        result = result.dropna()
        
        logger.info("Added technical indicators: RSI, MACD, Bollinger Bands")
        return result
    
    def create_target_variables(self, df: pd.DataFrame, forward_periods: List[int] = [1, 7, 30]) -> pd.DataFrame:
        """
        Create target variables for regression/classification.
        
        Args:
            df (DataFrame): Price data
            forward_periods (list): List of future periods
            
        Returns:
            DataFrame: Data with target variables
        """
        # Create copy to avoid modifying original data
        result = df.copy()
        
        # Create target variables
        for period in forward_periods:
            # Future price
            result[f'price_future_{period}d'] = result['price_usd'].shift(-period)
            
            # Price change
            result[f'price_change_{period}d'] = result[f'price_future_{period}d'] - result['price_usd']
            
            # Percentage return
            result[f'return_{period}d'] = (result[f'price_future_{period}d'] / result['price_usd']) - 1
            
            # Binary direction (up or down)
            result[f'direction_{period}d'] = (result[f'price_change_{period}d'] > 0).astype(int)
        
        logger.info("Added target variables for periods: %s", forward_periods)
        return result
    
    def generate_all_features(self, coin_id: str, forward_periods: List[int] = [1, 7, 30],
                              save_csv: bool = True, plot_features: bool = True) -> pd.DataFrame:
        """
        Generate all features for a coin.
        
        Args:
            coin_id (str): Coin ID
            forward_periods (list): List of future periods for target variables
            save_csv (bool): Whether to save results as CSV
            plot_features (bool): Whether to generate feature plots
            
        Returns:
            DataFrame: Data with all features
        """
        logger.info("Generating features for %s", coin_id)
        
        # Load price data
        df = self.load_price_data(coin_id)
        
        if df.empty:
            logger.error("No price data available for %s", coin_id)
            return df
        
        # Generate features
        df = self.create_time_features(df)
        df = self.create_lagged_features(df)
        df = self.create_rolling_features(df)
        df = self.create_technical_indicators(df)
        df = self.create_target_variables(df, forward_periods)
        
        # Save to CSV
        if save_csv:
            csv_path = os.path.join(self.output_dir, f"{coin_id}_features.csv")
            df.to_csv(csv_path)
            logger.info("Saved features to %s", csv_path)
        
        # Generate plots
        if plot_features:
            self._generate_plots(df, coin_id)
        
        return df
    
    def _generate_plots(self, df: pd.DataFrame, coin_id: str):
        """
        Generate plots for features.
        
        Args:
            df (DataFrame): Feature data
            coin_id (str): Coin ID
        """
        try:
            # Price plot
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['price_usd'], label='Price (USD)')
            plt.title(f"{coin_id} Price History")
            plt.xlabel('Date')
            plt.ylabel('Price (USD)')
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(self.plots_dir, f"{coin_id}_price_history.png"))
            plt.close()
            
            # Rolling means
            if 'price_mean_7d' in df.columns and 'price_mean_30d' in df.columns:
                plt.figure(figsize=(12, 6))
                plt.plot(df.index, df['price_usd'], label='Price (USD)', alpha=0.5)
                plt.plot(df.index, df['price_mean_7d'], label='7-day MA')
                plt.plot(df.index, df['price_mean_30d'], label='30-day MA')
                plt.title(f"{coin_id} Price with Moving Averages")
                plt.xlabel('Date')
                plt.ylabel('Price (USD)')
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(self.plots_dir, f"{coin_id}_moving_averages.png"))
                plt.close()
            
            # Bollinger Bands
            if all(col in df.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
                plt.figure(figsize=(12, 6))
                plt.plot(df.index, df['price_usd'], label='Price (USD)', alpha=0.5)
                plt.plot(df.index, df['bb_upper'], label='Upper Band', linestyle='--')
                plt.plot(df.index, df['bb_middle'], label='Middle Band')
                plt.plot(df.index, df['bb_lower'], label='Lower Band', linestyle='--')
                plt.title(f"{coin_id} Price with Bollinger Bands")
                plt.xlabel('Date')
                plt.ylabel('Price (USD)')
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(self.plots_dir, f"{coin_id}_bollinger_bands.png"))
                plt.close()
            
            # RSI
            if 'rsi_14' in df.columns:
                plt.figure(figsize=(12, 6))
                plt.plot(df.index, df['rsi_14'])
                plt.axhline(y=70, color='r', linestyle='--', alpha=0.5)
                plt.axhline(y=30, color='g', linestyle='--', alpha=0.5)
                plt.title(f"{coin_id} Relative Strength Index (RSI)")
                plt.xlabel('Date')
                plt.ylabel('RSI')
                plt.grid(True)
                plt.savefig(os.path.join(self.plots_dir, f"{coin_id}_rsi.png"))
                plt.close()
            
            # MACD
            if all(col in df.columns for col in ['macd', 'macd_signal']):
                plt.figure(figsize=(12, 6))
                plt.plot(df.index, df['macd'], label='MACD')
                plt.plot(df.index, df['macd_signal'], label='Signal Line')
                plt.bar(df.index, df['macd_histogram'], label='Histogram', alpha=0.3)
                plt.title(f"{coin_id} MACD")
                plt.xlabel('Date')
                plt.ylabel('MACD')
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(self.plots_dir, f"{coin_id}_macd.png"))
                plt.close()
            
            logger.info("Generated plots for %s", coin_id)
            
        except Exception as e:
            logger.error("Error generating plots: %s", str(e))

if __name__ == "__main__":
    setup_logging()
    fe = FeatureEngineering()
    
    # Example: Generate features for bitcoin
    df = fe.generate_all_features(coin_id='bitcoin')
