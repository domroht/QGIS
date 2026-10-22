import fitdecode


def extract_activity_data(file_path):

    session_data = {}

    with fitdecode.FitReader(file_path) as fit:
        for frame in fit:
            if (
                isinstance(frame, fitdecode.FitDataMessage)
                and frame.name == "session"
            ):
                session_data = {
                    field.name: field.value
                    for field in frame.fields
                }
                break

    return {
        "start_time": session_data.get("start_time"),
        "total_distance": session_data.get("total_distance"),
        "total_timer_time": session_data.get("total_timer_time"),
        "total_elapsed_time": session_data.get("total_elapsed_time"),
        "total_ascent": session_data.get("total_ascent"),
        "avg_speed": session_data.get("avg_speed"),
    }


def extract_gps_points(file_path):

    gps_points = []

    with fitdecode.FitReader(file_path) as fit:
        for frame in fit:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue

            if frame.name != "record":
                continue

            data = {
                field.name: field.value
                for field in frame.fields
            }

            lat_raw = data.get("position_lat")
            lon_raw = data.get("position_long")

            if lat_raw is None or lon_raw is None:
                continue

            # kordinator bliver gemt i halvcirkler som 32 signed int
            lat = lat_raw * (180 / 2**31)
            lon = lon_raw * (180 / 2**31)

            if not (-90 <= lat <= 90):
                continue

            if not (-180 <= lon <= 180):
                continue

            gps_points.append([lon, lat])

    return gps_points