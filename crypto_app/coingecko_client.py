"""
Módulo para interactuar con la API de CoinGecko.
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# Clave API desde variable de entorno o hardcodeada para desarrollo
API_KEY = os.environ.get('COINGECKO_API_KEY', 'CG-E61ywJ7ucHsXH96nDttVtmcG')

class CoinGeckoAPI:
    """Cliente para la API de CoinGecko."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key=None):
        """
        Inicializa el cliente API.
        
        Args:
            api_key (str, optional): La clave API para autenticación.
                                    Si es None, se usa API_KEY del módulo.
        """
        self.api_key = api_key or API_KEY
        self.session = requests.Session()
        # Construir URL con la clave API como parámetro de consultas
        self.session.headers.update({
            # La API gratuita usa 'x-cg-demo-api-key' como encabezado
            'x-cg-demo-api-key': self.api_key,
            'User-Agent': 'CryptoDataPipeline/1.0'
        })
    
    def get_coin_history(self, coin_id, date):
        """
        Obtiene los datos históricos de una moneda en una fecha específica.
        
        Args:
            coin_id (str): El ID de la moneda (ej., 'bitcoin')
            date (str): La fecha en formato dd-mm-yyyy
            
        Returns:
            dict: Los datos históricos de la moneda
        """
        endpoint = f"{self.BASE_URL}/coins/{coin_id}/history"
        params = {'date': date}
        
        logger.debug("Solicitando datos desde %s con parámetros %s", endpoint, params)
        
        max_retries = 3
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint, params=params)
                response.raise_for_status()
                
                logger.debug("La solicitud API fue exitosa con código de estado %s", response.status_code)
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Límite de velocidad excedido
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning("Límite de velocidad excedido. Reintentando después de %s segundos.", retry_after)
                    time.sleep(retry_after)
                    continue
                
                # Loguear información de error más detallada
                logger.error("Ocurrió un error HTTP: %s", e)
                try:
                    error_response = response.json()
                    logger.error("Detalles del error de la API: %s", error_response)
                except:
                    logger.error("Contenido de respuesta sin procesar: %s", response.text)
                if attempt < max_retries - 1:
                    logger.info("Reintentando en %s segundos (intento %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error("Ocurrió un error de solicitud: %s", e)
                if attempt < max_retries - 1:
                    logger.info("Reintentando en %s segundos (intento %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
        # Si llegamos aquí, todos los reintentos fallaron
        raise requests.exceptions.RequestException("No se pudo obtener los datos después de múltiples intentos")
    
    def get_coin_list(self):
        """
        Obtiene la lista de todas las monedas disponibles.
        
        Returns:
            list: Lista de monedas disponibles con sus IDs
        """
        endpoint = f"{self.BASE_URL}/coins/list"
        
        logger.debug("Solicitando lista de monedas desde %s", endpoint)
        
        max_retries = 3
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint)
                response.raise_for_status()
                
                logger.debug("La solicitud API fue exitosa con código de estado %s", response.status_code)
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                logger.error("Ocurrió un error HTTP: %s", e)
                if attempt < max_retries - 1:
                    logger.info("Reintentando en %s segundos (intento %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error("Ocurrió un error de solicitud: %s", e)
                if attempt < max_retries - 1:
                    logger.info("Reintentando en %s segundos (intento %s/%s)", retry_delay, attempt + 1, max_retries)
                    time.sleep(retry_delay)
                else:
                    raise
                    
        # Si llegamos aquí, todos los reintentos fallaron
        raise requests.exceptions.RequestException("No se pudo obtener la lista de monedas después de múltiples intentos")
