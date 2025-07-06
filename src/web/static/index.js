fetch('/api/polygons')
    .then(response => response.json())
    .then(data => {
        const geoLayer = L.geoJSON(data, {
            style: function (feature) {
                // Style polygons based on damage_type
                switch (feature.properties.damage_type) {
                    case 'severe': return { color: "red" };
                    case 'moderate': return { color: "orange" };
                    case 'minor': return { color: "yellow" };
                }
            },
            onEachFeature: function (feature, layer) {
                // Popup with info
                layer.bindPopup(
                    `Type: ${feature.properties.damage_type}<br>
           Confidence: ${feature.properties.confidence}<br>
           Notes: ${feature.properties.notes}`
                );
            }
        }).addTo(map);

        // Center and zoom map to fit all polygons
        if (geoLayer.getLayers().length > 0) {
            map.fitBounds(geoLayer.getBounds());
        }
    });
