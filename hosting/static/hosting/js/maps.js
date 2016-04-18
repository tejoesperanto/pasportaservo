$(document).ready(function() {
    // HTML5 Geolocation API
    var onLocationFound = function(e){
        setPositionFields([e.latitude, e.longitude]);
        marker.setLatLng([e.latitude, e.longitude]);
    };

    // Init the map and marker
    var latitude = $("#id_latitude").val();
    var longitude = $("#id_longitude").val();
    var initLatLng = [40, 0];
    var initZoom = 1;
    if (latitude || longitude) {
        initLatLng = [latitude, longitude];
        initZoom = 18;
    }
    var attribution = 'Mapaj datumoj &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> kontribuantoj';
    var placeEditMap = L.map('place-edit-map').setView(initLatLng, initZoom);
    L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: attribution
    }).addTo(placeEditMap);
    var marker = L.marker(initLatLng, {draggable:true}).addTo(placeEditMap);

    // Hide fields in form
    $("#id_latitude").closest('.form-group').hide();
    $("#id_longitude").closest('.form-group').hide();

    var setPositionFields = function(latlng) {
        $("#id_latitude").val(latlng.lat);
        $("#id_longitude").val(latlng.lng);
    };

    var onMapClick = function(e) {
        setPositionFields(e.latlng);
        marker.setLatLng(e.latlng);
        placeEditMap.setView(e.latlng, placeEditMap.getZoom()+2);  /* Center and Zoom x2 */
    };

    var onMarkerDrag = function(e) {
        setPositionFields(e.target.getLatLng());
        placeEditMap.setView(e.target.getLatLng());  /* Center */
    };

    placeEditMap.on('click', onMapClick);
    marker.on('dragend', onMarkerDrag);

    // Click on the 'Where I am?' button
    $('#get-location').click(function(e) {
        placeEditMap.on('locationfound', onLocationFound);
        placeEditMap.locate({setView: true});
    });
});
