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
    "Pool": "#0080FF"
};

fetch('/api/polygons')
    .then(response => response.json())
    .then(data => {
        const geoLayer = L.geoJSON(data, {
            style: function (feature) {
                const cls = feature.properties.class;
                return {
                    color: classColorMap[cls] || "#FFFFFF",
                    fillColor: classColorMap[cls] || "#FFFFFF",
                    fillOpacity: 0.5,
                    weight: 2
                };
            },
            onEachFeature: function (feature, layer) {
                layer.bindPopup(
                    `<strong>Class:</strong> ${feature.properties.class}<br>
           <strong>Confidence:</strong> ${feature.properties.confidence || ""}<br>
           <strong>Notes:</strong> ${feature.properties.notes || ""}`
                );
            }
        }).addTo(map);

        if (geoLayer.getLayers().length > 0) {
            map.fitBounds(geoLayer.getBounds());
        }
    });


// Example using fetch API
fetch('/ask_gemma', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: "Summarize the damage in this area." })
})
    .then(res => res.json())
    .then(data => {
        alert(data.response); // Display Gemma's answer
    });
