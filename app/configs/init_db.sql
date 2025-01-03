-- store locations
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

-- store forecasts data
-- disable foreign key for now: location_id INTEGER REFERENCES locations (id)
CREATE TABLE IF NOT EXISTS forecasts (
    id SERIAL PRIMARY KEY,
    location_id INTEGER,
    date DATE,
    time TIME,
    temperature NUMERIC(5,2)
);