// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/world-map.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener("load", function() {

    mapboxgl.setRTLTextPlugin('https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-rtl-text/v0.1.2/mapbox-gl-rtl-text.js');

    var map = new mapboxgl.Map({
        container: 'map',
        style: '/mapo/positron-gl-style.json',
        hash: true,
        minZoom: 1.5,
        maxZoom: 15,
        zoom: 1.5,
        center: [10, 20]
    });

    map.on('load', function() {
        var nav = new mapboxgl.NavigationControl();
        map.addControl(nav, 'top-left'),

        map.addSource("lokoj", {
            type: "geojson",
            data: '/mapo/lokoj.geojson',
            cluster: true,
            clusterMaxZoom: 14, // Max zoom to cluster points on
            clusterRadius: 50 // Radius of each cluster when clustering points (defaults to 50)
        });

        map.addLayer({
            id: "clusters",
            type: "circle",
            source: "lokoj",
            filter: ["has", "point_count"],
            paint: {
                "circle-color": {
                    property: "point_count",
                    type: "interval",
                    stops: [
                        [0, "#FF9242"],
                        [10, "#FFC36B"],
                        [100, "#FFD96B"],
                    ]
                },
                "circle-radius": {
                    property: "point_count",
                    type: "interval",
                    stops: [
                        [0, 12],
                        [10, 20],
                        [100, 26]
                    ]
                }
            }
        });

        map.addLayer({
            id: "cluster-count",
            type: "symbol",
            source: "lokoj",
            filter: ["has", "point_count"],
            layout: {
                "text-field": "{point_count}",
                "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
                "text-size": 11
            }
        });

        map.addLayer({
            id: "places",
            type: "circle",
            source: "lokoj",
            filter: ["!has", "point_count"],
            paint: {
                "circle-color": "#ff7711",
                "circle-radius": 5,
                "circle-stroke-width": 1,
                "circle-stroke-color": "#fff"
            }
        });
        map.on('click', 'places', function(e) {
            function htmlEscape(value) {
                return value.replace(/&/g,  "&amp;")
                            .replace(/"/g,  "&#34;").replace(/'/g,  "&#39;")
                            .replace(/</g,  "&lt;") .replace(/>/g,  "&gt;")
                            .replace(/\//g, "&#47;");
            }
            var TEMPLATE = '<h4><a href="[URL]">[NAME] de <strong>[CITY]</strong></a></h4>';
            var popupHtml = "";
            e.features.forEach(function(feature) {
                var p = feature.properties;
                popupHtml += TEMPLATE.replace("[URL]", p.url)
                                     .replace("[NAME]", htmlEscape(p.owner_name))
                                     .replace("[CITY]", htmlEscape(p.city));
            });
            new mapboxgl.Popup()
                .setLngLat(e.features[0].geometry.coordinates)
                .setHTML(popupHtml)
                .addTo(map);
        });

        map.on('click', 'clusters', function(e) {
            map.flyTo({
                center: e.lngLat,
                zoom: map.getZoom() + 2,
            });
        });

        // Change the cursor to a pointer when the mouse is over the clusters layer.
        map.on('mouseenter', 'clusters', function() {
            map.getCanvas().style.cursor = "pointer";
        });

        // Change it back to a hand when it leaves.
        map.on('mouseleave', 'clusters', function() {
            map.getCanvas().style.cursor = "";
        });

        // Change the cursor to a pointer when the mouse is over the places layer.
        map.on('mouseenter', 'places', function() {
            map.getCanvas().style.cursor = "pointer";
        });

        // Change it back to a hand when it leaves.
        map.on('mouseleave', 'places', function() {
            map.getCanvas().style.cursor = "";
        });
    });

});


// @license-end
