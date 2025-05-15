"""
Module for handling database operations.
"""
import os
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# La variable de entorno DATABASE_URL debe tener el formato:
# postgresql://username:password@host:port/database
DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/crypto_data"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

class Database:
    """Class for handling database operations."""
    
    def __init__(self, db_url=None):
        """
        Initialize the database connection.
        
        Args:
            db_url (str, optional): URL de conexión a la base de datos.
        """
        self.db_url = db_url or DATABASE_URL
        self.engine = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(self.db_url)
            logger.info("Connected to database: %s", self.db_url.split('@')[1] if '@' in self.db_url else self.db_url)
            return True
        except Exception as e:
            logger.error("Error connecting to database: %s", str(e))
            return False
    
    def initialize_db(self):
        """Initialize the database by executing the SQL script."""
        if not self.engine:
            if not self.connect():
                return False
        
        try:
            # Read and execute the SQL script
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'sql', 
                'create_tables.sql'
            )
            with open(script_path, 'r') as f:
                sql_script = f.read()
            
            with self.engine.begin() as conn:
                conn.execute(text(sql_script))
                # begin() maneja el commit automáticamente
            
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.error("Error initializing database: %s", str(e))
            return False
    
    def save_coin_data(self, coin_id: str, date_obj: datetime.date, data: Dict[str, Any]) -> bool:
        """
        Save coin data to the database.
        
        Args:
            coin_id (str): Coin ID
            date_obj (datetime.date): Date of the data
            data (dict): Coin data from the API
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not self.engine:
            if not self.connect():
                return False
        
        try:
            # Extract the price in USD from the data
            price_usd = None
            if data.get('market_data') and data['market_data'].get('current_price'):
                price_usd = data['market_data']['current_price'].get('usd')
            
            # Conectar directamente con psycopg2 para evitar problemas de SQLAlchemy
            import psycopg2
            from psycopg2.extras import Json
            
            # Extraer los parámetros de conexión de la URL
            conn_parts = self.db_url.replace('postgresql://', '').split('@')
            user_pass = conn_parts[0].split(':')
            host_db = conn_parts[1].split('/')
            host_port = host_db[0].split(':')
            
            # Crear conexión directa
            conn = psycopg2.connect(
                host=host_port[0],
                port=host_port[1] if len(host_port) > 1 else 5432,
                dbname=host_db[1],
                user=user_pass[0],
                password=user_pass[1]
            )
            cursor = conn.cursor()
            
            # Verificar si ya existe un registro
            check_query = "SELECT COUNT(*) FROM coin_history WHERE coin_id = %s AND fetch_date = %s"
            cursor.execute(check_query, (coin_id, date_obj))
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                # Actualizar registro existente
                update_query = """
                UPDATE coin_history 
                SET price_usd = %s, response_data = %s, created_at = %s
                WHERE coin_id = %s AND fetch_date = %s
                """
                cursor.execute(update_query, (price_usd, Json(data), datetime.now().date(), coin_id, date_obj))
            else:
                # Insertar nuevo registro
                insert_query = """
                INSERT INTO coin_history 
                (coin_id, price_usd, fetch_date, response_data, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (coin_id, price_usd, date_obj, Json(data), datetime.now().date()))
            
            # Actualizar agregados mensuales
            self._update_monthly_aggregates_psycopg2(cursor, coin_id, date_obj.year, date_obj.month)
            
            # Commit y cerrar
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("Data saved to database for %s on %s", coin_id, date_obj)
            return True
        
        except Exception as e:
            logger.error("Error saving data to database: %s", str(e))
            return False
            
    def _update_monthly_aggregates_psycopg2(self, cursor, coin_id: str, year: int, month: int):
        """
        Update monthly aggregates for a specific coin using psycopg2.
        
        Args:
            cursor: Database cursor
            coin_id (str): Coin ID
            year (int): Year
            month (int): Month (1-12)
        """
        try:
            # Calculate min/max for the month
            min_max_query = """
            SELECT 
                MIN(price_usd) as min_price, 
                MAX(price_usd) as max_price
            FROM coin_history
            WHERE coin_id = %s
            AND EXTRACT(YEAR FROM fetch_date) = %s
            AND EXTRACT(MONTH FROM fetch_date) = %s
            AND price_usd IS NOT NULL
            """
            
            cursor.execute(min_max_query, (coin_id, year, month))
            result = cursor.fetchone()
            
            if result and (result[0] is not None or result[1] is not None):
                min_price, max_price = result
                
                # Insert or update aggregate record
                upsert_query = """
                INSERT INTO coin_monthly_aggregates 
                (coin_id, year, month, min_price_usd, max_price_usd, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (coin_id, year, month)
                DO UPDATE SET
                    min_price_usd = %s,
                    max_price_usd = %s,
                    updated_at = CURRENT_TIMESTAMP
                """
                
                cursor.execute(upsert_query, (coin_id, year, month, min_price, max_price, min_price, max_price))
                
                logger.info("Monthly aggregates updated for %s in %s-%s", coin_id, year, month)
        
        except Exception as e:
            logger.error("Error updating monthly aggregates: %s", str(e))
            # Don't raise exception to avoid interrupting the main transaction
    
    def _update_monthly_aggregates(self, conn, coin_id: str, year: int, month: int):
        """
        Update monthly aggregates for a specific coin.
        
        Args:
            conn: Database connection
            coin_id (str): Coin ID
            year (int): Year
            month (int): Month (1-12)
        """
        try:
            # Calculate min/max for the month
            stmt = text("""
                SELECT 
                    MIN(price_usd) as min_price, 
                    MAX(price_usd) as max_price
                FROM coin_history
                WHERE coin_id = %(coin_id)s
                AND EXTRACT(YEAR FROM fetch_date) = %(year)s
                AND EXTRACT(MONTH FROM fetch_date) = %(month)s
                AND price_usd IS NOT NULL
            """)
            
            result = conn.execute(stmt, {'coin_id': coin_id, 'year': year, 'month': month}).fetchone()
            
            if result and (result[0] is not None or result[1] is not None):
                min_price, max_price = result
                
                # Insert or update aggregate record
                stmt = text("""
                    INSERT INTO coin_monthly_aggregates 
                    (coin_id, year, month, min_price_usd, max_price_usd, updated_at)
                    VALUES (%(coin_id)s, %(year)s, %(month)s, %(min_price)s, %(max_price)s, CURRENT_TIMESTAMP)
                    ON CONFLICT (coin_id, year, month)
                    DO UPDATE SET
                        min_price_usd = %(min_price)s,
                        max_price_usd = %(max_price)s,
                        updated_at = CURRENT_TIMESTAMP
                """)
                
                conn.execute(stmt, {
                    'coin_id': coin_id,
                    'year': year,
                    'month': month,
                    'min_price': min_price,
                    'max_price': max_price
                })
                
                logger.info("Monthly aggregates updated for %s in %s-%s", coin_id, year, month)
        
        except Exception as e:
            logger.error("Error updating monthly aggregates: %s", str(e))
            # Don't raise exception to avoid interrupting the main transaction
    
    def get_monthly_aggregates(self, coin_id: str, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """
        Get monthly aggregates for a coin.
        
        Args:
            coin_id (str): Coin ID
            year (int, optional): Filter by year
            month (int, optional): Filter by month
            
        Returns:
            list: List of monthly aggregates
        """
        if not self.engine:
            if not self.connect():
                return []
        
        try:
            with self.engine.connect() as conn:
                query = "SELECT coin_id, year, month, min_price_usd, max_price_usd FROM coin_monthly_aggregates WHERE coin_id = %(coin_id)s"
                params = {'coin_id': coin_id}
                
                if year is not None:
                    query += " AND year = %(year)s"
                    params['year'] = year
                
                if month is not None:
                    query += " AND month = %(month)s"
                    params['month'] = month
                
                query += " ORDER BY year DESC, month DESC"
                
                results = conn.execute(text(query), params).fetchall()
                
                return [
                    {
                        'coin_id': r[0],
                        'year': r[1],
                        'month': r[2],
                        'min_price_usd': float(r[3]) if r[3] is not None else None,
                        'max_price_usd': float(r[4]) if r[4] is not None else None
                    } 
                    for r in results
                ]
                
        except Exception as e:
            logger.error("Error retrieving monthly aggregates: %s", str(e))
            return []
    
    def run_analysis_query(self, query_name: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Run a named analysis query from the SQL file.
        
        Args:
            query_name (str): Name of the query in the analysis_queries.sql file
            params (dict, optional): Parameters for the query
            
        Returns:
            list: Query results as a list of dictionaries
        """
        if not self.engine:
            if not self.connect():
                return []
        
        try:
            # Load analysis queries
            query_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'sql', 
                'analysis_queries.sql'
            )
            
            # Extract named query from the file
            if not os.path.exists(query_path):
                logger.error("Analysis queries file not found: %s", query_path)
                return []
            
            with open(query_path, 'r') as f:
                sql_content = f.read()
            
            # Extract the requested query using markers
            query_start = f"-- BEGIN {query_name}"
            query_end = f"-- END {query_name}"
            
            start_pos = sql_content.find(query_start)
            if start_pos == -1:
                logger.error("Query not found: %s", query_name)
                return []
            
            start_pos = sql_content.find("\n", start_pos) + 1
            end_pos = sql_content.find(query_end, start_pos)
            
            if end_pos == -1:
                logger.error("End marker not found for query: %s", query_name)
                return []
            
            query = sql_content[start_pos:end_pos].strip()
            
            # Execute the query
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                
                # Convert result to list of dictionaries
                columns = result.keys()
                rows = []
                
                for row in result:
                    row_dict = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        # Convert decimal types to float for JSON serialization
                        if isinstance(value, Decimal):
                            value = float(value)
                        row_dict[column] = value
                    rows.append(row_dict)
                
                return rows
                
        except Exception as e:
            logger.error("Error running analysis query '%s': %s", query_name, str(e))
            return []
