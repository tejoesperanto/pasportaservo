// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/place-map.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener('load', function() {

    var container = document.getElementById('map');
    if (!container) {
        return;
    }
    var position = container.hasAttribute('data-marker') ? container.getAttribute('data-marker') : '';
    var positionType = container.getAttribute('data-marker-type') || 'R';
    try {
        position = position.trim() ? JSON.parse(position) : undefined;
    }
    catch (e) {
        position = undefined;
    }
    var mediaPrint = container.hasAttribute('data-for-print');
    var attrib = GIS_ENDPOINTS['place_map_attrib'];
    var staticUseNoticeNode = document.querySelector('#map ~ .static-map-auto-switch');

    mapboxgl.setRTLTextPlugin(GIS_ENDPOINTS['rtl_plugin'], undefined, true);

    if (staticUseNoticeNode) {
        if (!mapboxgl.supported()) {
            var staticFallback = container.parentElement.querySelector('noscript');
            staticFallback.outerHTML = staticFallback.innerHTML;
            if (staticUseNoticeNode.getAttribute('data-notification')) {
                staticUseNoticeNode.textContent = staticUseNoticeNode.getAttribute('data-notification');
                staticUseNoticeNode.removeAttribute('data-notification');
                staticUseNoticeNode.classList.remove("empty");
                staticUseNoticeNode.classList.add("has-content");
            }
            else {
                staticUseNoticeNode.remove();
            }
            return;
        }
        else {
            staticUseNoticeNode.remove();
        }
    }

    // If WebGL is unsupported or disabled, the exception "Failed to initialize WebGL" will
    // be thrown. This should not impact other code on the page, and only affect this event
    // handler specifically.

    var map = new mapboxgl.Map({
        container: 'map',
        style: GIS_ENDPOINTS['place_map_style'],
        locale: (mapboxgl.localui || {})[document.documentElement.lang],
        // http://fuzzytolerance.info/blog/2016/07/01/Printing-Mapbox-GL-JS-maps-in-Firefox
        preserveDrawingBuffer: navigator.userAgent.toLowerCase().indexOf('firefox') > -1,
        attributionControl: attrib !== undefined ? Boolean(attrib) : true,
        pitchWithRotate: false,
        minZoom: 0.5,
        maxZoom: positionType == 'P' ? 17 : 15,
        zoom: position ? 14 : 0.5,
        center: position ? position.geometry.coordinates : [-175, 75]
    });
    if (positionType == 'R') {
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

    map.on('styledata', function() {
        container.style.backgroundImage = "none";
        container.style.backgroundColor = "transparent";
    });

    map.on('load', function() {
        map.addControl(new mapboxgl.NavigationControl(), 'top-left');
        map.addControl(new mapboxgl.FullscreenControl(), 'top-right');
        if (positionType == 'P' || positionType == 'C') {
            var loc = new mapboxgl.GeolocateControl({
                positionOptions: {
                    enableHighAccuracy: true
                },
                fitBoundsOptions: {
                    maxZoom: 17
                }
            });
            map.addControl(loc, 'top-left');
        }

        if (position) {
            map.addSource("thisplace", {
                type: "geojson",
                data: position
            });
            if (positionType == 'C') {
                map.addLayer({
                    id: "host-marker",
                    type: "circle",
                    source: "thisplace",
                    paint: {
                        "circle-color": "#1bf",
                        "circle-opacity": [
                            "interpolate", ["linear"], ["zoom"],
                            12, !mediaPrint ? 0.70 : 0.30,
                            15, !mediaPrint ? 0.07 : 0.03,
                        ],
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
                        "circle-stroke-width": !mediaPrint ? 1 : 2,
                        "circle-stroke-opacity": !mediaPrint ? 1.00 : 0.10,
                        "circle-stroke-color": !mediaPrint ? "#eee" : "#000"
                    }
                });
            }
            if (positionType == 'P') {
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
