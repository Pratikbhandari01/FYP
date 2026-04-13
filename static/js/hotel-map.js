document.addEventListener("DOMContentLoaded", function () {
    const mapContainer = document.getElementById("hotelMap");
    const mapStatus = document.getElementById("mapStatus");
    const dataElement = document.getElementById("hotel-map-data");

    if (!mapContainer || !dataElement || typeof L === "undefined") {
        return;
    }

    let hotels = [];
    try {
        hotels = JSON.parse(dataElement.textContent || "[]");
    } catch (error) {
        if (mapStatus) {
            mapStatus.textContent = "Could not read hotel map data.";
        }
        return;
    }

    const map = L.map(mapContainer).setView([27.7172, 85.3240], 7);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    if (!hotels.length) {
        if (mapStatus) {
            mapStatus.textContent = "No hotels available to display.";
        }
        return;
    }

    const markerGroup = L.featureGroup().addTo(map);

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    async function geocodeLocation(location) {
        const trimmed = (location || "").trim();
        if (!trimmed) {
            return null;
        }

        const endpoint = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(trimmed);
        const response = await fetch(endpoint, {
            headers: {
                "Accept": "application/json",
            },
        });

        if (!response.ok) {
            return null;
        }

        const data = await response.json();
        if (!Array.isArray(data) || !data.length) {
            return null;
        }

        const first = data[0];
        const lat = Number(first.lat);
        const lon = Number(first.lon);
        if (Number.isNaN(lat) || Number.isNaN(lon)) {
            return null;
        }

        return { lat, lon };
    }

    async function renderMarkers() {
        if (mapStatus) {
            mapStatus.textContent = "Geocoding hotel locations...";
        }

        let markerCount = 0;

        for (const hotel of hotels) {
            try {
                const coords = await geocodeLocation(hotel.location);
                if (!coords) {
                    continue;
                }

                const marker = L.marker([coords.lat, coords.lon]);
                const popupHtml =
                    '<strong>' + escapeHtml(hotel.name) + '</strong><br>' +
                    '<span>' + escapeHtml(hotel.location || "Unknown location") + '</span><br>' +
                    '<a href="' + escapeHtml(hotel.url) + '">View rooms</a>';

                marker.bindPopup(popupHtml);
                marker.addTo(markerGroup);
                markerCount += 1;

                await new Promise((resolve) => setTimeout(resolve, 220));
            } catch (error) {
                // Ignore per-hotel geocoding failures and continue building map markers.
            }
        }

        if (markerCount > 0) {
            map.fitBounds(markerGroup.getBounds().pad(0.2));
            if (mapStatus) {
                mapStatus.textContent = markerCount + " hotel marker(s) loaded.";
            }
        } else {
            if (mapStatus) {
                mapStatus.textContent = "No map markers could be resolved from hotel locations.";
            }
        }
    }

    renderMarkers();
});
