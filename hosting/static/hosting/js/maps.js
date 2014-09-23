function placeEdit(map, options){
    // HTML5 Geolocation API
    function onLocationFound(e){
        setPositionFields([e.latitude, e.longitude]);
        marker.setLatLng([e.latitude, e.longitude]);
    }
    map.on('locationfound', onLocationFound);
    map.locate({setView: true});

    // Init the map and marker
    var latitude = $("#id_latitude").val();
    var longitude = $("#id_longitude").val();
    var initLatLng = [40, 0];
    var initZoom = 1;
    if (latitude || longitude) {
        initLatLng = [latitude, longitude];
        initZoom = 18;
    }
    map.setView(initLatLng, initZoom);
    var marker = L.marker(initLatLng, {draggable:true}).addTo(map);

    // Hide fields in form
    $("#id_latitude").closest('.form-group').hide();
    $("#id_longitude").closest('.form-group').hide();

    function setPositionFields(latlng) {
        $("#id_latitude").val(latlng.lat);
        $("#id_longitude").val(latlng.lng);
    };

    function onMapClick(e) {
        setPositionFields(e.latlng);
        marker.setLatLng(e.latlng);
        map.setView(e.latlng, map.getZoom()+2);  /* Center and Zoom x2 */
    };

    function onMarkerDrag(e) {
        setPositionFields(e.target.getLatLng());
        map.setView(e.target.getLatLng());  /* Center */
    };

    map.on('click', onMapClick);
    marker.on('dragend', onMarkerDrag);
};
