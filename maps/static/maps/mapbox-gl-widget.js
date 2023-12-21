// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/maps/static/maps/mapbox-gl-widget.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


window.addEventListener('load', function() {

    var fieldLocation = document.getElementById('id_location'),
        fieldCoordinates = document.getElementById('id_coordinates');
    var submit = document.getElementById('id_form_submit');
    var selectOnlyOnZoom,
        initial;

    try {
        initial = JSON.parse(fieldLocation.value).coordinates;
    } catch (error) {
        initial = undefined;
    }
    if (fieldLocation.hasAttribute('data-selectable-zoom') && submit != undefined) {
        selectOnlyOnZoom = Number(fieldLocation.getAttribute('data-selectable-zoom'));
        submit.setAttribute('data-initial-title', submit.title);
    }

    mapboxgl.setRTLTextPlugin(GIS_ENDPOINTS['rtl_plugin'], undefined, true);

    var map = new mapboxgl.Map({
        container: 'map',
        style: GIS_ENDPOINTS['widget_style'],
        locale: (mapboxgl.localui || {})[document.documentElement.lang],
        attributionControl: false,
        pitchWithRotate: false,
        minZoom: 1,
        maxZoom: 17,
        zoom: initial ? 14 : 1.5,
        center: initial || [10, 20]
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();

    map.on('load', function() {
        var marker, markerBase = new mapboxgl.Marker({color: '#428bca'});

        if (initial) {
            map.setCenter(initial);
            marker = markerBase
                .setLngLat(initial)
                .addTo(map);
        }
        else if (selectOnlyOnZoom) {
            submit.disabled = true;
        }

        map.getCanvas().style.cursor = "pointer";

        var clickListener = function(e, manualUpdate, withZoom) {
            if (marker) {
                marker.setLngLat(e.lngLat);
            }
            else {
                marker = markerBase
                    .setLngLat(e.lngLat)
                    .addTo(map);
            }

            var zoomLevel = withZoom !== undefined ? withZoom : map.getZoom();
            map.flyTo({
                center: e.lngLat,
                zoom: zoomLevel + (manualUpdate !== true ? 2 : 0),
            });

            fieldLocation.value = JSON.stringify({
                type: "Point",
                coordinates: [e.lngLat.lng, e.lngLat.lat]
            });
            if (fieldCoordinates && manualUpdate !== true) {
                fieldCoordinates.value = "[LAT], [LNG]"
                    .replace("[LNG]", e.lngLat.lng)
                    .replace("[LAT]", e.lngLat.lat);
                fieldCoordinates.removeAttribute('data-complex-validation-failed');
                fieldCoordinates.dispatchEvent(
                    new Event('change', {bubbles: true, cancelable: true})
                );
            }
            if (selectOnlyOnZoom) {
                submit.disabled = (zoomLevel < selectOnlyOnZoom);
                submit.title = (!submit.disabled) ?
                    submit.getAttribute('data-initial-title') :
                    gettext("Please zoom in the map to select a point.");
            }
        };
        map.on('click', clickListener);
        if (fieldCoordinates) {
            fieldCoordinates.mapref = map;
            fieldCoordinates.mapClick = clickListener;
        }

        var nav = new mapboxgl.NavigationControl({showCompass: false});
        map.addControl(nav, 'top-left');
        var scr = new mapboxgl.FullscreenControl();
        map.addControl(scr, 'top-right');
        var loc = new mapboxgl.GeolocateControl({
            positionOptions: {
                enableHighAccuracy: true
            },
            fitBoundsOptions: {
                maxZoom: 17
            }
        });
        map.addControl(loc, 'top-right');
        var scale = new mapboxgl.ScaleControl();
        map.addControl(scale, 'bottom-right');

        document.getElementById('map').style.backgroundImage = "none";
        document.getElementById('map').style.backgroundColor = "unset";
    });

});


// @license-end
