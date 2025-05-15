#!/usr/bin/env python3
"""
Script para cargar datos JSON de la carpeta data/ a la base de datos PostgreSQL.
Solo es necesario ejecutar si se descargaron datos desde la crypro_app sin la opción '--store-db'
"""
import os
import json
import glob
from datetime import datetime
import psycopg2
from psycopg2.extras import Json

# Configuración de la base de datos
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

def connect_to_database():
    """Conectarse a la base de datos PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print(f"Conexión exitosa a la base de datos {DB_NAME}")
        return conn
    except Exception as e:
        print(f"Error al conectarse a la base de datos: {e}")
        return None

def load_json_data(file_path):
    """Cargar datos desde un archivo JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar el archivo {file_path}: {e}")
        return None

def parse_date_from_filename(filename):
    """Extraer la fecha del nombre del archivo."""
    # Formato esperado: bitcoin_YYYY-MM-DD.json
    try:
        date_str = filename.split('_')[1].split('.')[0]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        print(f"Error al parsear la fecha del archivo {filename}: {e}")
        return None

def extract_price_usd(data):
    """Extraer el precio en USD de los datos JSON."""
    try:
        # Asumiendo una estructura como en la API de CoinGecko
        if "market_data" in data and "current_price" in data["market_data"]:
            return data["market_data"]["current_price"].get("usd")
        return None
    except Exception as e:
        print(f"Error al extraer el precio: {e}")
        return None

def insert_data_to_db(conn, coin_id, fetch_date, price_usd, json_data):
    """Insertar datos en la tabla coin_history."""
    try:
        cursor = conn.cursor()
        
        # Comprobar si ya existe un registro con el mismo coin_id y fetch_date
        cursor.execute(
            "SELECT COUNT(*) FROM coin_history WHERE coin_id = %s AND fetch_date = %s",
            (coin_id, fetch_date)
        )
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Ya existe un registro para {coin_id} en la fecha {fetch_date}. Actualizando...")
            cursor.execute(
                """
                UPDATE coin_history 
                SET price_usd = %s, response_data = %s, created_at = CURRENT_TIMESTAMP
                WHERE coin_id = %s AND fetch_date = %s
                """,
                (price_usd, Json(json_data), coin_id, fetch_date)
            )
        else:
            cursor.execute(
                """
                INSERT INTO coin_history (coin_id, price_usd, fetch_date, response_data, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (coin_id, price_usd, fetch_date, Json(json_data))
            )
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al insertar datos: {e}")
        conn.rollback()
        return False

def main():
    """Función principal para cargar todos los archivos JSON en la base de datos."""
    # Conectar a la base de datos
    conn = connect_to_database()
    if not conn:
        return
    
    # Buscar carpetas de monedas en data/
    coin_dirs = [d for d in glob.glob("data/*") if os.path.isdir(d)]
    
    total_files = 0
    loaded_files = 0
    
    for coin_dir in coin_dirs:
        coin_id = os.path.basename(coin_dir)
        print(f"\nProcesando archivos para {coin_id}...")
        
        # Buscar archivos JSON en la carpeta de la moneda
        json_files = glob.glob(f"{coin_dir}/*.json")
        
        for json_file in json_files:
            total_files += 1
            filename = os.path.basename(json_file)
            
            # Extraer fecha del nombre del archivo
            fetch_date = parse_date_from_filename(filename)
            if not fetch_date:
                continue
            
            # Cargar datos JSON
            data = load_json_data(json_file)
            if not data:
                continue
            
            # Extraer precio
            price_usd = extract_price_usd(data)
            
            # Insertar en la base de datos
            if insert_data_to_db(conn, coin_id, fetch_date, price_usd, data):
                loaded_files += 1
                print(f"Cargado {filename} correctamente.")
            else:
                print(f"Error al cargar {filename} en la base de datos.")
    
    if conn:
        conn.close()
    
    print(f"\nResumen: Cargados {loaded_files} de {total_files} archivos en la base de datos.")

if __name__ == "__main__":
    main()
