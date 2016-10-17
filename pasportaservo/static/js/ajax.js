// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/ajax.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {

    $('.ajax').click(function(e) {
        e.preventDefault();
        $this = $(this);
        $this.addClass('disabled');
        $.ajax({
            type: "POST",
            url: $this.attr('href'),
            data: {'csrfmiddlewaretoken': $this.data('csrf')},
            dataType: "json",
            success: function(response) {
                // TODO: Make it generic
                $this.parents('.remove-after-success').slideUp();
            },
            error: function() {
                // TODO: Inform the user about the error in intelligible manner
                $this.removeClass('disabled');
            }
        });
    });

});


// @license-end
