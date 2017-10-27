// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/mapbox-gl-widget.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener("load", function() {

    var field = document.getElementById('id_location');

    try {
        var initial = JSON.parse(field.value).coordinates;
    } catch (error) {
        var initial = undefined;
    }

    var map = new mapboxgl.Map({
        container: 'map',
        style: '/mapo/positron-gl-style.json',
        minZoom: 1,
        maxZoom: 17,
        zoom: 1.5,
        center: initial || [10, 20]
    });

    map.on('load', function() {
        if (initial) {
            map.setCenter(initial);

            var marker = new mapboxgl.Marker()
                .setLngLat(initial)
                .addTo(map);
        }

        map.getCanvas().style.cursor = 'pointer';

        map.on('click', function(e) {
            if (marker) {
                marker.setLngLat(e.lngLat);
            }
            else {
                var marker = new mapboxgl.Marker()
                    .setLngLat(e.lngLat)
                    .addTo(map);
            }

            map.flyTo({
                center: e.lngLat,
                zoom: map.getZoom() + 2,
            });

            field.value = JSON.stringify({
                type: "Point",
                coordinates: [e.lngLat.lng, e.lngLat.lat]
            })

        });

        var nav = new mapboxgl.NavigationControl();
        map.addControl(nav, 'top-left');
    });

});


// @license-end
