const classColorMap = {
    "Background": "#000000",
    "Water": "#00BFFF",
    "Building-No-Damage": "#A0522D",
    "Building-Medium-Damage": "#FFFF00",
    "Building-Major-Damage": "#FFA500",
    "Building-Total-Destruction": "#FF0000",
    "Vehicle": "#FF00FF",
    "Road-Clear": "#808080",
    "Road-Blocked": "#808000",
    "Tree": "#00FF00",
    "Pool": "#0080FF",
    "center": "#3399FF",
    "building_damage": "#FF0000",   // add these
    "roof_damage": "#FFA500"
};

// Fetch and render GeoJSON from backend
fetch('/api/polygons')
    .then(response => response.json())
    .then(data => {
        const geoLayer = L.geoJSON(data, {
            pointToLayer: function (feature, latlng) {
                // render center points as circle markers
                if (feature.geometry.type === "Point") {
                    return L.circleMarker(latlng, {
                        radius: 6,
                        color: feature.properties.color || classColorMap["center"],
                        fillColor: feature.properties.color || classColorMap["center"],
                        fillOpacity: 0.9
                    });
                }
                return L.marker(latlng);
            },
            style: function (feature) {
                if (feature.geometry.type === "Polygon") {
                    const cls = feature.properties.class;
                    return {
                        color: classColorMap[cls] || "#FFFFFF",
                        fillColor: classColorMap[cls] || "#FFFFFF",
                        fillOpacity: 0.5,
                        weight: 2
                    };
                }
                return {};  // default style
            },
            onEachFeature: function (feature, layer) {
                const props = feature.properties || {};
                let popup = `<strong>Class:</strong> ${props.class || 'N/A'}`;
                if (props.confidence !== undefined) popup += `<br><strong>Confidence:</strong> ${props.confidence}`;
                if (props.notes) popup += `<br><strong>Notes:</strong> ${props.notes}`;
                if (props.image) popup += `<br><strong>Image:</strong> ${props.image}`;
                if (props.created_at) popup += `<br><small><em>${props.created_at}</em></small>`;

                layer.bindPopup(popup);
            }
        }).addTo(map);

        if (geoLayer.getLayers().length > 0) {
            map.fitBounds(geoLayer.getBounds());
        }
    })
    .catch(err => {
        console.error("Failed to load polygons:", err);
        alert("Failed to load polygon data.");
    });

