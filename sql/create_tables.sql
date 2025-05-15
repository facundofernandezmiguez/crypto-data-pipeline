-- SQL script para crear las tablas en PostgreSQL

-- Tabla para almacenar los datos detallados de cada moneda
CREATE TABLE IF NOT EXISTS coin_history (
    id SERIAL PRIMARY KEY,
    coin_id VARCHAR(50) NOT NULL,
    price_usd NUMERIC(24, 8),
    fetch_date DATE NOT NULL,
    response_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (coin_id, fetch_date)
);

-- Índices para mejorar el rendimiento de las consultas
CREATE INDEX IF NOT EXISTS idx_coin_history_coin_id ON coin_history(coin_id);
CREATE INDEX IF NOT EXISTS idx_coin_history_date ON coin_history(fetch_date);

-- Tabla para almacenar los datos agregados por mes
CREATE TABLE IF NOT EXISTS coin_monthly_aggregates (
    id SERIAL PRIMARY KEY,
    coin_id VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    min_price_usd NUMERIC(24, 8),
    max_price_usd NUMERIC(24, 8),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (coin_id, year, month)
);

-- Índices para mejorar el rendimiento de las consultas
CREATE INDEX IF NOT EXISTS idx_coin_monthly_aggregates_coin_id ON coin_monthly_aggregates(coin_id);
CREATE INDEX IF NOT EXISTS idx_coin_monthly_aggregates_year_month ON coin_monthly_aggregates(year, month);

-- Comentarios para documentar el propósito de cada tabla
COMMENT ON TABLE coin_history IS 'Almacena datos históricos diarios de monedas desde CoinGecko';
COMMENT ON TABLE coin_monthly_aggregates IS 'Almacena precios mínimos y máximos mensuales de cada moneda';
