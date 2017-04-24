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

    function ajaxSetup($this) {
        var setupCallback = window[$this.data('on-ajax-setup')];
        if (typeof(setupCallback) === 'function') {
            return setupCallback($this);
        };
    }

    function ajaxPerform($this, target, requestType, requestData) {
        $this.addClass('disabled');
        $.ajax({
            type: requestType,
            url: target,
            csrfmiddlewaretoken: $this.data('csrf'),
            data: requestData,
            dataType: "json",
            success: function(response) {
                var successCallback = window[$this.data('on-ajax-success')];
                $this.removeClass('disabled');
                if (typeof(successCallback) === 'function') {
                    successCallback($this, response);
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
    }

    // allow interaction for any element and on any event
    $('[class*=ajax]').each(function() {
        var $this = $(this);
        var re = /\bajax-on-([a-z]+)\b/gi;
        var has_events = false;
        while ((event = re.exec(this.className)) !== null) {
            $this.on(event[1].toLowerCase(), function(e) {
                if (ajaxSetup($this) === false)
                    return;

                var target = $this.data('ajaxAction');
                var requestType = $this.data('ajaxMethod') || "GET";
                var requestData = $this.serialize();
                if (!target) {
                    target = $this.parents('form').attr('action');
                    requestType = $this.parents('form').attr('method');
                    requestData = $this.parents('form').serialize();
                }
                if ($this.data('csrf') === undefined) {
                    $this.data('csrf', $this.parents('form').data('csrf'));
                }

                ajaxPerform($this, target, requestType, requestData);
            });
            has_events = true;
        }
        if (has_events) {
            $this.focus(function() {
                $this.popover("destroy");
            });
        }
    });

    // basic case of <a> or <button> element with a click event
    $('.ajax').click(function(e) {
        e.preventDefault();
        var $this = $(this), target, requestType;
        if ($this.is('a')) {
            target = $this.attr('href');
            requestType = $this.data('method') || "GET";
        }
        else {
            // should be a button within a form
            target = $this.parents('form').attr('action');
            requestType = $this.parents('form').attr('method');
        }
        ajaxPerform($this, target, requestType);
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

    window.blockPlaceSetup = function($this) {
        if ($this.val() == $this.data('value')) {
            return false;
        }
        $this.closest('form').find('#id_dirty').val($this.get(0).name);
    };

    window.blockPlaceSuccess = function($this, response) {
        var $op_errors = $this.closest('form').find('.blocking-errors');
        if (response.result === false) {
            $this.parents('.form-group').addClass('has-error');
            var specific_errors = response.err[$this.get(0).name],
                general_errors = response.err["__all__"];
            $op_errors.text([specific_errors != undefined ? specific_errors.join(" ") : undefined,
                             general_errors != undefined ? general_errors.join(" ") : undefined].join("\n"));
            $op_errors.show();
        }
        if (response.result === true) {
            $this.parents('.form-group').removeClass('has-error');
            $op_errors.text("");
            $op_errors.hide();
            var $marker = $this.closest('form').find('.blocking-success');
            $marker.css({ "visibility": "visible", "opacity": 1 })
                   .delay(2000)
                   .animate({ opacity: 0 }, 400, function() { $(this).css("visibility", "hidden"); });
            $this.data('value', $this.val());
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
