$(document).ready(function() {
    if("geolocation" in navigator) {
        $('#gps').click(function(e) {
            e.preventDefault();
            $(this).html('<img src="/static/img/gps_spinner.gif" />');
            navigator.geolocation.getCurrentPosition(function(position) {
                $('#searchinput').val(position.coords.latitude + ',' + position.coords.longitude);
                $('#searchform').submit();
            });
        });
    }
});
