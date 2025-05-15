#!/usr/bin/env python3
"""
Script para ejecutarse diariamente mediante cron/programador de tareas para obtener datos de criptomonedas específicas.
Este script debe programarse para ejecutarse a las 3am.
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import click
from pathlib import Path

from crypto_app.coingecko_client import CoinGeckoAPI
from crypto_app.db import Database
from crypto_app.cli import setup_logging, _process_single_date

@click.command()
@click.option('--store-db', is_flag=True, help='Almacenar datos en la base de datos PostgreSQL')
def daily_fetch(store_db):
    """
    Proceso diario de obtención de datos para monedas criptográficas predeterminadas.
    Diseñado para ejecutarse mediante cron/programador de tareas diariamente a las 3am.
    """
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Monedas objetivo para obtener datos
    coins = ["bitcoin", "ethereum", "cardano"]
    
    # Usar la fecha de ayer por defecto
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    logger.info("=== Iniciando obtención diaria de datos de criptomonedas para %s ===", date_str)
    
    success_count = 0
    for coin in coins:
        logger.info("Procesando %s para %s", coin, date_str)
        try:
            if _process_single_date(coin, yesterday, store_db):
                success_count += 1
                logger.info("Procesado exitosamente %s", coin)
            else:
                logger.error("Error al procesar %s", coin)
        except Exception as e:
            logger.error("Error al procesar %s: %s", coin, str(e))
    
    total_coins = len(coins)
    logger.info("=== Completada obtención diaria: %s/%s monedas procesadas exitosamente ===", 
                success_count, total_coins)
    
    # Devolver mensaje resumen
    click.echo(f"Obtención diaria completada: {success_count}/{total_coins} monedas procesadas exitosamente.")

def setup_windows_task():
    """
    Función para ayudar a configurar la tarea en el Programador de tareas de Windows.
    Imprime instrucciones para configurar la tarea.
    """
    script_path = os.path.abspath(__file__)
    python_exe = sys.executable
    
    # Imprimir instrucciones para el Programador de tareas de Windows
    print("\n=== Instrucciones de configuración del Programador de tareas de Windows ===")
    print("1. Abrir el Programador de tareas (taskschd.msc)")
    print("2. Hacer clic en 'Crear tarea básica...'")
    print("3. Nombre: CryptoDataDailyFetch")
    print("4. Descripción: Obtener datos de criptomonedas diariamente a las 3am")
    print("5. Desencadenador: Diariamente, comenzando a las 3:00 AM")
    print("6. Acción: Iniciar un programa")
    print(f"7. Programa/script: {python_exe}")
    print("8. Argumentos: -m crypto_app.daily_fetch --store-db")
    print(f"9. Iniciar en: {os.path.dirname(os.path.dirname(script_path))}")
    print("10. Finalizar el asistente y marcar 'Abrir el diálogo de propiedades...'")
    print("11. En el diálogo de Propiedades, ir a la pestaña 'Configuración'")
    print("12. Marcar 'Ejecutar la tarea lo antes posible después de que se haya perdido una ejecución programada'")
    print("13. Hacer clic en Aceptar para guardar\n")

def setup_linux_cron():
    """
    Función para ayudar a configurar la tarea cron en Linux.
    Imprime instrucciones para configurar la tarea cron.
    """
    script_path = os.path.abspath(__file__)
    project_path = os.path.dirname(os.path.dirname(script_path))
    
    # Generar entrada para crontab
    cron_entry = f"0 3 * * * cd {project_path} && python -m crypto_app.daily_fetch --store-db >> {project_path}/logs/cron.log 2>&1"
    
    # Imprimir instrucciones para cron de Linux
    print("\n=== Instrucciones de configuración de Cron en Linux ===")
    print("Ejecuta el siguiente comando para editar tu crontab:")
    print("  crontab -e")
    print("\nLuego añade esta línea para programar la tarea diariamente a las 3am:")
    print(f"  {cron_entry}\n")

if __name__ == "__main__":
    # Si se ejecuta con el argumento --setup, mostrar instrucciones de configuración
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        if sys.platform.startswith('win'):
            setup_windows_task()
        else:
            setup_linux_cron()
    else:
        # De lo contrario, ejecutar el proceso de obtención diaria
        daily_fetch()
