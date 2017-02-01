$(document).ready(function() {
    if("geolocation" in navigator) {
        $('#gps').click(function(e) {
            e.preventDefault();
            $('.search-marker', this).hide();
            $('.search-working', this).show();
            
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    console.log(position);
                    $('#searchinput').val(position.coords.latitude + ',' + position.coords.longitude);
                    $('#searchform').submit();
                },
                function(error) {
                    if(typeof error === 'function') { // Happens on some browsers.
                        return;
                    }
                    
                    if(error.code == 1) {
                        // User canceled position detection.
                        $('.search-working', this).hide();
                        $('.search-marker', this).show();
                    } else {
                        console.log(error);
                        $('.search-working', this).hide();
                        $('.search-marker', this).show();
                        alert("Your position couldn't be determined.");
                    }
                }
            );
        });
    } else {
        $('#gps').remove();
    }
});
