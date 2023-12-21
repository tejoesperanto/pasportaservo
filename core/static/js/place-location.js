// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/place-location.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(function() {

    $('#id_coordinates').on('input', function(event) {
        this.removeAttribute('data-complex-validation-failed');
        if (typeof this.mapref !== "undefined" && this.value.trim()) {
            var field = this, coordinates, lnglat;
            if (typeof field.pattern !== "undefined") {
                // constraint validation happens only after this handler, so it is better to
                // check explicitely the validity of the typed (or pasted) input.
                if (new RegExp(field.pattern).test(field.value))
                    coordinates = field.value;
            }
            else {
                // no pattern defined: we must work with possibly bad data. it will cause an
                // exception when trying to convert to the `LngLat` object.
                coordinates = field.value;
            }
            if (!coordinates)
                return;
            coordinates = coordinates.trim().replace(/(\s+,?\s*|\s*,?\s+)/, ",").split(",");
            try {
                lnglat = mapboxgl.LngLat.convert([coordinates[1], coordinates[0]]).wrap();
            }
            catch (e) {
                field.setAttribute('data-complex-validation-failed', gettext("Bad or impossible coordinates."));
                return;
            }
            var lng_precision = coordinates[1].indexOf(".") >= 0 ? coordinates[1].split(".")[1].length : 0,
                lat_precision = coordinates[0].indexOf(".") >= 0 ? coordinates[0].split(".")[1].length : 0,
                precision = Math.min(lng_precision, lat_precision);
            var zoomLevel;
            // the decimal precision defines the zoom level of the map -- that is, how many
            // details are visible, -- which in turn defines if the value can be submitted.
            // see https://docs.mapbox.com/help/glossary/zoom-level/
            // and https://en.wikipedia.org/wiki/Decimal_degrees#Precision
            if (precision <= 6) {
                zoomLevel = Math.min([0, 3, 6, 9, 13, 16, 19][precision], field.mapref.getMaxZoom());
            }
            else {
                zoomLevel = field.mapref.getMaxZoom();
            }
            field.mapClick({lngLat: lnglat}, true, zoomLevel);
        }
    });

    if (!$('#id_coordinates').closest('.form-group').hasClass('has-error')) {
        $('#id_coordinates').siblings('[id^="hint_"]').first().prepend(gettext("Alternatively: "));
    }

});


// @license-end
