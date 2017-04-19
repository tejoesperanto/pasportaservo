// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/ajax.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {

    function isCSRFSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!isCSRFSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", settings.csrfmiddlewaretoken);
            }
        }
    });

    $('.ajax').click(function(e) {
        e.preventDefault();
        $this = $(this);
        $this.addClass('disabled');
        if ($this.is('a')) {
            target = $this.attr('href');
            requestType = $this.data('method') || "GET";
        }
        else {
            // should be a button within a form
            target = $this.parents('form').attr('action');
            requestType = $this.parents('form').attr('method');
        }
        $.ajax({
            type: requestType,
            url: target,
            dataType: "json",
            csrfmiddlewaretoken: $this.data('csrf'),
            success: function(response) {
                successCallback = window[$this.data('on-ajax-success')];
                if (typeof(successCallback) === 'function') {
                    successCallback($this);
                }
            },
            error: function(xhr) {
                $this.removeClass('disabled');
                $this.popover({
                    trigger: "focus",
                    container: 'body',
                    placement: "bottom",
                    html: true,
                    title: ((document.documentElement.lang == "eo") ? "Servila eraro" : "Server error") + " (" + xhr.status + ")",
                    content: "<span class='help-block'>" +
                             ((document.documentElement.lang == "eo") ?
                              "Io misfunkciis. Bonvole reprovu; <br class='visible-xxs-inline'>se la eraro denove okazas, <a href='{url}'>kontaktu nin</a>." :
                              "Something misfunctioned.<br>Please retry; if the error repeats itself, please <a href='{url}'>contact us</a>."
                             ).replace("{url}", "mailto:saluton [cxe] pasportaservo.org").replace(" [cxe] ", "@") +
                             "</span>"
                }).popover("show");
            }
        });
    });

    $('.ajax').focus(function(e) {
        $(this).popover("destroy");
    });

    var ditchForm = function($this) {
        $this.unwrap('.unwrap-after-success');
        $this.prev('[name="csrfmiddlewaretoken"]').remove();
    };

    window.confirmInfoSuccess = function($this) {
        $this.parents('.remove-after-success').slideUp();
    };

    window.verifyEmailSuccess = function($this) {
        ditchForm($this);
        $this.removeClass('ajax');
        $this.prop('disabled', true);
        if ($this.data('success-text')) {
            $this.text($this.data('success-text'));
            $this.addClass('btn-warning');
        }
        if ($this.data('success-message')) {
            $('#'+$this.data('success-message')).modal();
        }
    };

    window.checkPlaceSuccess = function($this) {
        ditchForm($this);
        $this.removeClass('ajax');
        $this.removeClass('btn-warning').addClass('btn-success');
        $this.closest('.callout').addClass('callout-success');
        if ($this.data('success-text')) {
            $this.text($this.data('success-text'));
        }
    };

    window.markInvalidEmailSuccess = function($this) {
        ditchForm($this);
        $this.prev('.email').addClass('text-danger').children('a').contents().unwrap('a');
        $this.remove();
    };

});


// @license-end
