// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/place-map.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener("load", function() {

    var container = document.getElementById('map');
    var location = container.hasAttribute('data-marker') ? container.getAttribute('data-marker') : '';
    var locationType = container.getAttribute('data-marker-type') || 'R';
    try {
        location = location.trim() ? JSON.parse(location) : undefined;
    }
    catch (e) {
        location = undefined;
    }

    mapboxgl.setRTLTextPlugin(GIS_ENDPOINTS['rtl_plugin']);

    var map = new mapboxgl.Map({
        container: 'map',
        style: GIS_ENDPOINTS['place_map_style'],
        pitchWithRotate: false,
        minZoom: 0.5,
        maxZoom: 15,
        zoom: location ? 14 : 0.5,
        center: location && location.geometry.coordinates || [-175, 75]
    });
    if (locationType == 'R') {
        try {
            var bbox = container.hasAttribute('data-bounds') ? container.getAttribute('data-bounds') : '';
            bbox = bbox.trim() ? JSON.parse(bbox) : undefined;
            map.setZoom(12);  // We have to set the zoom before setting the point to center on.
            map.jumpTo({center: bbox.features[0].geometry.coordinates});
            if (bbox.features.length > 1) {
                map.fitBounds(bbox.features[1].geometry.coordinates);
            }
        }
        catch (e) {
        }
    }

    map.on('load', function() {
        var nav = new mapboxgl.NavigationControl();
        map.addControl(nav, 'top-left');

        if (location) {
            map.addSource("thisplace", {
                type: "geojson",
                data: location
            });
            if (locationType == 'C') {
                map.addLayer({
                    id: "host-marker",
                    type: "circle",
                    source: "thisplace",
                    paint: {
                        "circle-color": "#1bf",
                        "circle-opacity": 0.7,
                        "circle-radius": [
                            "interpolate", ["linear"], ["zoom"],
                            1, 3,
                            9, 3,
                            10, 6,
                            11, 13,
                            12, 27,
                            13, 55,
                            14, 110,
                            15, 220,
                        ],
                        "circle-stroke-width": 1,
                        "circle-stroke-color": "#eee"
                    }
                });
            }
            if (locationType == 'P') {
                map.addLayer({
                    id: "host-marker",
                    type: "circle",
                    source: "thisplace",
                    paint: {
                        "circle-color": "#f71",
                        "circle-opacity": 1.0,
                        "circle-radius": 6,
                        "circle-stroke-width": 1,
                        "circle-stroke-color": "#fff"
                    }
                });
            }
        }
    });

});


// @license-end
