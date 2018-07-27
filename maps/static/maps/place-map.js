// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/place-map.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener("load", function() {

    var container = document.getElementById('map');
    var location = container.hasAttribute('data-marker') ? container.getAttribute('data-marker').trim() : '';
    try {
        location = location != '' ? JSON.parse(location): undefined;
    }
    catch (e) {
        location = undefined;
    }

    mapboxgl.setRTLTextPlugin(GIS_ENDPOINTS['rtl_plugin']);

    var map = new mapboxgl.Map({
        container: 'map',
        style: GIS_ENDPOINTS['place_map_style'],
        minZoom: 0.5,
        maxZoom: 15,
        zoom: location ? 14 : 0.5,
        center: location || [-175, 75]
    });

    map.on('load', function() {
        var nav = new mapboxgl.NavigationControl();
        map.addControl(nav, 'top-left');

        if (location) {
            map.addSource("thisplace", {
                type: "geojson",
                data: {"type": "Feature", "geometry": {"type": "Point", "coordinates": [location.lng, location.lat]}}
            });

            map.addLayer({
                id: "host-marker",
                type: "circle",
                source: "thisplace",
                paint: {
                    "circle-color": "#ff7711",
                    "circle-opacity": 1.0,
                    "circle-radius": 6,
                    "circle-stroke-width": 1,
                    "circle-stroke-color": "#fff"
                }
            });
        }
    });

});


// @license-end
