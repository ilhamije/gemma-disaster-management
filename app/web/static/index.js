// === Map Initialization ===
const map = L.map('map').setView([0, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
}).addTo(map);

// === Status Elements ===
const uploadStatus = document.getElementById("uploadStatus");
const progressSpinner = document.getElementById("progressSpinner");

// === Class Colors ===
const classColorMap = {
    "background": "#000000",
    "water": "#00BFFF",
    "building-no-damage": "#A0522D",
    "building-medium-damage": "#FFFF00",
    "building-major-damage": "#FFA500",
    "building-total-destruction": "#FF0000",
    "vehicle": "#FF00FF",
    "road-clear": "#808080",
    "road-blocked": "#808000",
    "tree": "#00FF00",
    "pool": "#0080FF",
    "center": "#3399FF",
};

// === Helpers ===
function normalizeClassName(name) {
    return name ? name.toString().trim().toLowerCase() : "background";
}

function fixFeatures(data) {
    if (!data || !Array.isArray(data.features)) {
        console.warn("Invalid GeoJSON, returning empty collection");
        return { type: "FeatureCollection", features: [] };
    }

    const validFeatures = [];

    data.features.forEach(feature => {
        const geom = feature.geometry;
        if (!geom || !geom.type || !geom.coordinates) return;

        if (geom.type === "Polygon") {
            const ring = geom.coordinates[0];
            if (!Array.isArray(ring)) {
                console.warn("Invalid polygon, skipping", feature);
                return null;
            }
            if (!Array.isArray(ring) || ring.length < 4) {
                console.warn("Invalid polygon, skipping", feature);
                return;
            }
            // Ensure closed ring
            const first = ring[0], last = ring[ring.length - 1];
            if (first[0] !== last[0] || first[1] !== last[1]) {
                ring.push(first);
            }
            geom.coordinates = [ring];
        }
        else if (geom.type === "LineString") {
            if (!Array.isArray(geom.coordinates) || geom.coordinates.length < 2) {
                console.warn("Invalid LineString, skipping", feature);
                return;
            }
        }
        else if (geom.type === "Point") {
            if (!Array.isArray(geom.coordinates) || geom.coordinates.length !== 2) {
                console.warn("Invalid Point, skipping", feature);
                return;
            }
        }
        validFeatures.push(feature);
    });

    return {
        type: "FeatureCollection",
        features: validFeatures,
        properties: data.properties || {}
    };
}

function renderMap(data) {
    const geoLayer = L.geoJSON(data, {
        pointToLayer: function (feature, latlng) {
            const clsKey = normalizeClassName(feature.properties.class);
            return L.circleMarker(latlng, {
                radius: 6,
                color: classColorMap[clsKey] || "#FF00FF",
                fillColor: classColorMap[clsKey] || "#FF00FF",
                fillOpacity: 0.9
            });
        },
        style: function (feature) {
            const clsKey = normalizeClassName(feature.properties.class);
            return {
                color: classColorMap[clsKey] || "#FF00FF",
                fillColor: classColorMap[clsKey] || "#FF00FF",
                fillOpacity: 0.5,
                weight: 2
            };
        },
        onEachFeature: function (feature, layer) {
            const props = feature.properties || {};
            let popup = `<strong>Class:</strong> ${props.class || 'N/A'}`;
            if (props.confidence !== undefined) popup += `<br><strong>Confidence:</strong> ${props.confidence}`;
            if (props.notes) popup += `<br><strong>Notes:</strong> ${props.notes}`;
            if (props.created_at) popup += `<br><small><em>${props.created_at}</em></small>`;
            layer.bindPopup(popup);
        }
    });

    geoLayer.addTo(map);  // only once

    // Centering
    if (data.properties && data.properties.center_lat && data.properties.center_lon) {
        map.setView([data.properties.center_lat, data.properties.center_lon], 12);
    } else if (geoLayer.getLayers().length > 0) {
        map.fitBounds(geoLayer.getBounds());
    }

    // Processing status
    const waitingFeature = data.features.find(f => f.properties && f.properties.waiting);
    if (waitingFeature) {
        let countdown = 30;
        uploadStatus.textContent = `Processing analysis ... (${countdown}s)`;
        progressSpinner.style.display = "inline-block";

        const timer = setInterval(() => {
            countdown--;
            if (countdown > 0) {
                uploadStatus.textContent = `Processing analysis ... (${countdown}s)`;
            } else {
                clearInterval(timer);
                uploadStatus.textContent = "Still processing ... reload soon.";
                progressSpinner.style.display = "none";
            }
        }, 1000);
    } else {
        uploadStatus.textContent = "Analysis complete.";
        progressSpinner.style.display = "none";
    }
}


// === Initial Fetch ===
fetch('/api/polygons')
    .then(response => response.json())
    .then(data => {
        console.log("Polygon data:", data);
        renderMap(fixFeatures(data));
    })
    .catch(err => {
        console.error("Failed to load polygons:", err);
        alert("Failed to load polygon data.");
    });
