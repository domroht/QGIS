CREATE EXTENSION IF NOT EXISTS postgis;


CREATE TABLE IF NOT EXISTS routes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name TEXT NOT NULL,

    route_hash TEXT NOT NULL UNIQUE,

    route GEOMETRY(LineString, 4326) NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);


CREATE INDEX IF NOT EXISTS routes_route_idx
ON routes
USING GIST (route);

CREATE TABLE IF NOT EXISTS route_points (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    route_id BIGINT NOT NULL
        REFERENCES routes(id)
        ON DELETE CASCADE,

    sequence INTEGER NOT NULL,

    geom GEOMETRY(Point, 4326) NOT NULL,

    distance_from_start DOUBLE PRECISION,

    UNIQUE (route_id, sequence)
);

CREATE INDEX IF NOT EXISTS route_points_geom_idx
ON route_points
USING GIST (geom);

CREATE INDEX IF NOT EXISTS route_points_route_sequence_idx
ON route_points (route_id, sequence);