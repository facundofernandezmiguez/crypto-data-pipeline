-- Query 1: Precio promedio por moneda por mes
-- Calcula el precio promedio en USD por moneda, agrupado por año y mes.
-- Suposiciones: Incluye todos los datos disponibles; los precios nulos se excluyen.
SELECT 
    coin_id,
    EXTRACT(YEAR FROM fetch_date) AS year,
    EXTRACT(MONTH FROM fetch_date) AS month,
    ROUND(AVG(price_usd), 2) AS avg_price_usd
FROM coin_history
WHERE price_usd IS NOT NULL
GROUP BY coin_id, EXTRACT(YEAR FROM fetch_date), EXTRACT(MONTH FROM fetch_date)
ORDER BY coin_id, year, month;

-- Query 2: Precio promedio de aumento después de 3+ días consecutivos de caída
-- Identifica períodos donde el precio de una moneda cae por 3+ días consecutivos,
-- calcula el promedio de aumento porcentual al primer precio de recuperación (precio > precio más bajo durante la caída),
-- e incluye el último capital mercado desde response_data.
-- Suposiciones: 
-- - Una caída es cualquier día donde price_usd < precio del día anterior.
-- - La recuperación es el primer día después de la secuencia de caída donde el precio excede el precio más bajo en la secuencia.
-- - Utiliza todos los datos disponibles (no límite de rango de tiempo).
-- - Si market_cap_usd está ausente en JSON, devuelve NULL.
WITH daily_changes AS (
    SELECT
        coin_id,
        fetch_date,
        price_usd,
        LAG(price_usd) OVER (PARTITION BY coin_id ORDER BY fetch_date) AS prev_price,
        CASE 
            WHEN price_usd < LAG(price_usd) OVER (PARTITION BY coin_id ORDER BY fetch_date) 
            THEN 1 ELSE 0 
        END AS is_drop_day
    FROM coin_history
    WHERE price_usd IS NOT NULL
),
drop_sequences AS (
    SELECT
        coin_id,
        fetch_date,
        price_usd,
        is_drop_day,
        SUM(CASE WHEN is_drop_day = 0 THEN 1 ELSE 0 END) 
            OVER (PARTITION BY coin_id ORDER BY fetch_date) AS group_id
    FROM daily_changes
),
consecutive_drops AS (
    SELECT 
        coin_id,
        group_id,
        COUNT(*) AS consecutive_days,
        MIN(price_usd) AS lowest_price,
        MAX(fetch_date) AS end_date
    FROM drop_sequences
    WHERE is_drop_day = 1
    GROUP BY coin_id, group_id
    HAVING COUNT(*) >= 3
),
price_increases AS (
    SELECT 
        d.coin_id,
        d.lowest_price,
        d.end_date,
        MIN(h.fetch_date) AS recovery_date,
        h.price_usd AS recovery_price
    FROM consecutive_drops d
    JOIN coin_history h ON d.coin_id = h.coin_id 
        AND h.fetch_date > d.end_date 
        AND h.price_usd > d.lowest_price
    GROUP BY d.coin_id, d.lowest_price, d.end_date, h.price_usd
),
latest_market_cap AS (
    SELECT DISTINCT ON (coin_id)
        coin_id,
        response_data->>'market_cap_usd' AS current_market_cap_usd
    FROM coin_history
    ORDER BY coin_id, fetch_date DESC
)
SELECT 
    p.coin_id,
    ROUND(AVG((p.recovery_price - p.lowest_price) / p.lowest_price * 100), 2) AS avg_price_increase_pct,
    l.current_market_cap_usd
FROM price_increases p
LEFT JOIN latest_market_cap l ON p.coin_id = l.coin_id
GROUP BY p.coin_id, l.current_market_cap_usd
ORDER BY avg_price_increase_pct DESC;