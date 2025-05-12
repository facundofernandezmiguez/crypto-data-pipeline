-- SQL queries para análisis de datos de criptomonedas

/* NOTA IMPORTANTE:
 * Este archivo contiene consultas SQL de análisis que se utilizan a través de
 * la aplicación Python. Cuando se ejecutan directamente, estas consultas son
 * solo plantillas y deben modificarse con valores reales antes de su uso.
 * Los parámetros con ':' son reemplazados en tiempo de ejecución por la aplicación.
 */

-- BEGIN monthly_average_price
-- Consulta que calcula el precio promedio mensual para una moneda específica
-- EJEMPLO (reemplazar 'bitcoin' con la moneda deseada cuando se use en la aplicación)
SELECT 
    coin_id,
    EXTRACT(YEAR FROM fetch_date) AS year,
    EXTRACT(MONTH FROM fetch_date) AS month,
    AVG(price_usd) as avg_price_usd
FROM coin_history
WHERE coin_id = 'bitcoin'  -- En la aplicación se reemplaza con :coin_id
GROUP BY coin_id, EXTRACT(YEAR FROM fetch_date), EXTRACT(MONTH FROM fetch_date)
ORDER BY year DESC, month DESC;
-- END monthly_average_price

-- BEGIN price_recovery_analysis
-- Analiza cuántos días tarda un token en recuperar su valor después de una caída significativa
-- EJEMPLO (reemplazar 'bitcoin' y '-10' con valores deseados cuando se use en la aplicación)
WITH price_changes AS (
    SELECT
        coin_id,
        fetch_date,
        price_usd,
        LAG(price_usd) OVER (PARTITION BY coin_id ORDER BY fetch_date) AS prev_price,
        (price_usd - LAG(price_usd) OVER (PARTITION BY coin_id ORDER BY fetch_date)) / 
            NULLIF(LAG(price_usd) OVER (PARTITION BY coin_id ORDER BY fetch_date), 0) * 100 AS price_change_pct
    FROM coin_history
    WHERE coin_id = 'bitcoin'  -- En la aplicación se reemplaza con :coin_id
    AND price_usd IS NOT NULL
),
significant_drops AS (
    SELECT
        coin_id,
        fetch_date AS drop_date,
        price_usd AS drop_price,
        prev_price
    FROM price_changes
    WHERE price_change_pct <= -10  -- En la aplicación se reemplaza con :drop_threshold
),
recovery_dates AS (
    SELECT
        d.coin_id,
        d.drop_date,
        d.drop_price,
        d.prev_price,
        MIN(h.fetch_date) AS recovery_date
    FROM significant_drops d
    JOIN coin_history h ON d.coin_id = h.coin_id AND h.fetch_date > d.drop_date
    WHERE h.price_usd >= d.prev_price
    GROUP BY d.coin_id, d.drop_date, d.drop_price, d.prev_price
)
SELECT
    coin_id,
    drop_date,
    drop_price,
    prev_price,
    recovery_date,
    (recovery_date - drop_date) AS days_to_recovery
FROM recovery_dates
ORDER BY drop_date DESC;
-- END price_recovery_analysis

-- BEGIN volatility_analysis
-- Calcula la volatilidad (desviación estándar) para períodos mensuales
-- EJEMPLO (reemplazar 'bitcoin' con la moneda deseada cuando se use en la aplicación)
SELECT
    coin_id,
    EXTRACT(YEAR FROM fetch_date) AS year,
    EXTRACT(MONTH FROM fetch_date) AS month,
    STDDEV(price_usd) AS price_volatility,
    AVG(price_usd) AS avg_price,
    (STDDEV(price_usd) / AVG(price_usd) * 100) AS relative_volatility_pct
FROM coin_history
WHERE coin_id = 'bitcoin'  -- En la aplicación se reemplaza con :coin_id
AND price_usd IS NOT NULL
GROUP BY coin_id, EXTRACT(YEAR FROM fetch_date), EXTRACT(MONTH FROM fetch_date)
ORDER BY year DESC, month DESC;
-- END volatility_analysis

-- BEGIN correlation_analysis
-- Analiza la correlación entre dos monedas (requiere unión de tablas)
-- EJEMPLO (reemplazar 'bitcoin' y 'ethereum' con las monedas deseadas cuando se use en la aplicación)
WITH coin1_prices AS (
    SELECT 
        fetch_date, 
        price_usd AS price1
    FROM coin_history
    WHERE coin_id = 'bitcoin'  -- En la aplicación se reemplaza con :coin_id1
    AND price_usd IS NOT NULL
),
coin2_prices AS (
    SELECT 
        fetch_date, 
        price_usd AS price2
    FROM coin_history
    WHERE coin_id = 'ethereum'  -- En la aplicación se reemplaza con :coin_id2
    AND price_usd IS NOT NULL
),
combined_prices AS (
    SELECT 
        c1.fetch_date,
        c1.price1,
        c2.price2
    FROM coin1_prices c1
    JOIN coin2_prices c2 ON c1.fetch_date = c2.fetch_date
)
SELECT
    CORR(price1, price2) AS price_correlation,
    COUNT(*) AS data_points,
    MIN(fetch_date) AS period_start,
    MAX(fetch_date) AS period_end
FROM combined_prices;
-- END correlation_analysis
