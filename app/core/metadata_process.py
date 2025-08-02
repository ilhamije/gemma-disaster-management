# app/core/metadata_process.py
from PIL import Image, ExifTags
import json
import math
import os

def get_exif_data(image):
    """Extracts EXIF data from an image and decodes tag names."""
    exif = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            exif[decoded] = value
    return exif

def extract_lat_lon(exif):
    """Extracts (latitude, longitude) from EXIF GPSInfo if available."""
    if 'GPSInfo' not in exif:
        return None, None

    gps_info = exif['GPSInfo']

    def _safe_ratio(val):
        """Converts rational or tuple to float safely."""
        try:
            if isinstance(val, tuple):
                return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
            return float(val)
        except Exception:
            return 0.0

    def _convert(coord, ref):
        """Convert EXIF GPS format to float degrees."""
        d = _safe_ratio(coord[0])
        m = _safe_ratio(coord[1])
        s = _safe_ratio(coord[2])
        value = d + (m / 60.0) + (s / 3600.0)
        if ref in ['S', 'W']:
            value *= -1
        return value

    try:
        lat = _convert(gps_info[2], gps_info[1]) if 2 in gps_info and 1 in gps_info else None
        lon = _convert(gps_info[4], gps_info[3]) if 4 in gps_info and 3 in gps_info else None
    except Exception as e:
        lat, lon = None, None

    return lat, lon


def create_circle_polygon(lat, lon, radius=50, points=36):
    """Creates coordinates for a circular polygon around (lat, lon) in meters."""
    coords = []
    earth_radius = 6378137  # meters
    for i in range(points):
        angle = 2 * math.pi * i / points
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        dlat = dy / earth_radius
        dlon = dx / (earth_radius * math.cos(math.radians(lat)))
        coords.append([
            lon + math.degrees(dlon),
            lat + math.degrees(dlat)
        ])
    coords.append(coords[0])
    return coords

def process_image(image_path):
    """
    - Reads EXIF GPS, resizes image to 512px width, keeps aspect.
    - Returns GeoJSON with blue circle polygon at image's center coordinates.
    - Saves resized image with _resized_output.jpg suffix.
    """
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    image = Image.open(image_path)
    exif = get_exif_data(image)
    lat, lon = extract_lat_lon(exif)
    if lat is None or lon is None:
        raise ValueError("No GPS metadata found in this image.")

    width = 512
    height = int(image.size[1] * (512 / image.size[0]))
    try:
        # Pillow >= 10
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    except AttributeError:
        # Pillow < 10 fallback
        image = image.resize((width, height), Image.ANTIALIAS)

    polygon = create_circle_polygon(lat, lon)
    feature = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "id": "center_estimate",
                "color": "blue"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon]
            }
        }]
    }
    save_path = f"{base_name}_resized_output.jpg"
    image.save(save_path)
    return json.dumps(feature, indent=4)
