// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/mapbox-gl-widget.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener("load", function() {

    var field = document.getElementById('id_location');
    var submit = document.getElementById('id_form_submit');
    var selectOnlyOnZoom = undefined;

    try {
        var initial = JSON.parse(field.value).coordinates;
    } catch (error) {
        var initial = undefined;
    }
    if (field.hasAttribute('data-selectable-zoom') && submit != undefined) {
        selectOnlyOnZoom = Number(field.getAttribute('data-selectable-zoom'));
        submit.setAttribute('data-initial-title', submit.title);
    }

    var map = new mapboxgl.Map({
        container: 'map',
        style: '/mapo/positron-gl-style.json',
        minZoom: 1,
        maxZoom: 17,
        zoom: initial ? 14 : 1.5,
        center: initial || [10, 20]
    });

    map.on('load', function() {
        var marker = undefined;

        if (initial) {
            map.setCenter(initial);
            marker = new mapboxgl.Marker()
                .setLngLat(initial)
                .addTo(map);
        }
        else if (selectOnlyOnZoom) {
            submit.disabled = true;
        }

        map.getCanvas().style.cursor = 'pointer';

        map.on('click', function(e) {
            if (marker) {
                marker.setLngLat(e.lngLat);
            }
            else {
                marker = new mapboxgl.Marker()
                    .setLngLat(e.lngLat)
                    .addTo(map);
            }

            var zoomLevel = map.getZoom();
            map.flyTo({
                center: e.lngLat,
                zoom: zoomLevel + 2,
            });

            field.value = JSON.stringify({
                type: "Point",
                coordinates: [e.lngLat.lng, e.lngLat.lat]
            });
            if (selectOnlyOnZoom) {
                submit.disabled = (zoomLevel < selectOnlyOnZoom);
                submit.title = (!submit.disabled) ?
                    submit.getAttribute('data-initial-title') :
                    (document.documentElement.lang == "eo") ?
                        "Bonvole pliproksimigu la mapon por elekti punkton." :
                        "Please zoom in the map to select a point.";
            }
        });

        var nav = new mapboxgl.NavigationControl();
        map.addControl(nav, 'top-left');
    });

});


// @license-end
