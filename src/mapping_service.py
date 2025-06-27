# src/mapping_service.py
import folium
import json


class DisasterMap:
    def __init__(self):
        # Hurricane Michael affected area coordinates
        self.center_lat = 30.1558  # Mexico Beach, FL area
        self.center_lon = -85.4158

    def create_damage_map(self, damage_reports):
        """Create interactive map with damage assessments"""

        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )

        for report in damage_reports:
            # Since RescueNet may lack GPS, create synthetic coords
            # or use image metadata if available
            lat, lon = self.estimate_coordinates(report)

            # Color code by damage severity
            color = self.get_damage_color(report['damage_summary'])

            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                popup=self.create_popup(report),
                color=color,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)

        return m

    def estimate_coordinates(self, report):
        """Estimate coordinates for mapping (for demo purposes)"""
        # Create synthetic coordinates within Hurricane Michael area
        import random
        lat_offset = random.uniform(-0.05, 0.05)
        lon_offset = random.uniform(-0.05, 0.05)
        return (self.center_lat + lat_offset, self.center_lon + lon_offset)
