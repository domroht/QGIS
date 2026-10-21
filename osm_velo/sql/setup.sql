CREATE TABLE IF NOT EXISTS activities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT,
    activity_date TIMESTAMPTZ,
    route GEOMETRY(LineString, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS activities_route_idx
ON activities
USING GIST (route);
