// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/ajax.js
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

    function ajaxPerform($this, target, requestType, requestData, popoverTrigger) {
        $this.addClass('disabled');
        $this.attr('aria-busy', "true");
        $.ajax({
            type: requestType,
            url: target,
            csrfmiddlewaretoken: $this.data('csrf'),
            data: requestData,
            dataType: "json",
            success: function(response) {
                var successCallback = window[$this.data('on-ajax-success')];
                $this.removeClass('disabled');
                $this.attr('aria-busy', "false");
                if (typeof(successCallback) === 'function') {
                    successCallback($this, response);
                }
            },
            error: function(xhr) {
                var errorCallback = window[$this.data('on-ajax-error')];
                $this.removeClass('disabled');
                $this.attr('aria-busy', "false");
                if (typeof(errorCallback) === 'function') {
                    errorCallback($this, xhr);
                }
                if ($this.is(':hidden'))
                    return;
                var errorText;
                if (xhr.getResponseHeader('content-type') == 'text/plain' && xhr.responseText) {
                    errorText = xhr.responseText;
                }
                else {
                    errorText = interpolate(
                        gettext(
                            "Something misfunctioned.<br>" +
                            "Please retry; if the error repeats itself, please <a href='%(url)s'>contact us</a>."
                        ),
                        {'url': "mailto:saluton [cxe] pasportaservo.org".replace(" [cxe] ", "@")}, true
                     );
                }
                $this.popover({
                    trigger: popoverTrigger || "focus",
                    container: 'body',
                    placement: "bottom",
                    html: true,
                    title: gettext("Server error") + " (" + xhr.status + ")",
                    content: "<span class='help-block'>" + errorText + "</span>",
                }).popover("show");
            }
        });
    }
    $.ajaxManualCall = ajaxPerform

    // allow interaction for any element and on any event
    $('[class*=ajax]').each(function() {
        var $this = $(this);
        var re = /\bajax-on-([a-z]+)\b/gi;
        var event, has_events = false;
        while ((event = re.exec(this.className)) !== null) {
            $this.on(event[1].toLowerCase(), function(e) {
                if (ajaxSetup($this) === false)
                    return;

                var target = $this.data('ajaxAction');
                var requestType = $this.data('ajaxMethod') || "GET";
                var requestData = $this.serialize();
                if (!target) {
                    var $parentForm = $this.parents('form');
                    target = $parentForm.attr('action');
                    requestType = $parentForm.attr('method');
                    requestData = $parentForm.serialize();
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
        var $this = $(this), target, requestType, requestData;
        if (ajaxSetup($this) === false)
            return;
        if ($this.is('a')) {
            target = $this.attr('href');
            requestType = $this.data('method') || "GET";
        }
        else {
            // should be a button within a form
            var $parentForm = $this.parents('form');
            target = $parentForm.attr('action');
            requestType = $parentForm.attr('method');
            requestData = $parentForm.serialize();
        }
        ajaxPerform($this, target, requestType, requestData);
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
            var $op_notify = $('#'+$this.data('success-message'));
            var $op_content = $op_notify.find('[data-notification]');
            $op_content.text($op_content.data('notification'));
            $op_notify.data('relatedSource', $this);
            $op_notify.modal();
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
            var $notify = $(document.createElement('span')).addClass('sr-only')
                          .text($marker.data('notification'));
            $marker.css({ "visibility": "visible", "opacity": 1 })
                   .html($notify)
                   .delay(2000)
                   .animate({ opacity: 0 }, 400, function() {
                       $(this).css("visibility", "hidden");
                       $notify.remove();
                   });
            $this.data('value', $this.val());
        }
    };

    window.checkPlaceSetup = function($this) {
        if ($this.parents('.place-supervisor-detail').find('.text-surrogate').length > 0) {
            return window.confirm(window.checkPlaceTextSurrogateWarning);
        }
    };

    window.checkPlaceSuccess = function($this, response) {
        if (response.result === false) {
            var $op_notify = $('#'+$this.data('failure-message'));
            var $op_header = $op_notify.find('.modal-title');
            var $op_errors = $op_notify.find('ul');
            var general_errors = response.err__all__;
            $op_errors.empty();
            if (general_errors != undefined) {
                $op_errors.append($(document.createElement('li')).text(general_errors.join(" ⁕ ")));
            }
            for (var field in response.err) {
                $op_errors.append($(document.createElement('li')).html(
                    field + ": " + response.err[field].map(function(e) { return e.replace(/[.!]+$/g, "") }).join("; ")
                ));
            }
            $op_header.text($op_header.data('title'));
            $op_notify.data('relatedSource', $this);
            $op_notify.modal();
            $op_errors.parent()[0].scrollTop = 0;
        }
        if (response.result === true) {
            var cleanup = function() {
                ditchForm($this);
                $this.removeClass('ajax')
                     .removeClass('btn-warning').addClass('btn-success')
                     .width("auto");
                $this.closest('.callout').addClass('callout-success');
                if ($this.data('success-text')) {
                    $this.text($this.data('success-text'));
                }
            }
            var $marker = $this.siblings($this.data('process-elem') || "undefined");
            var buttonWidth = $this.width();
            $this.prop('disabled', true)
                 .removeData('hover-text').removeAttr('data-hover-text')
                 .removeData('hover-class').removeAttr('data-hover-class');
            if ($marker.length) {
                $this.html($marker).width(buttonWidth);
                $marker.show().delay(Math.random()*1500 + 1000)
                       .animate({ opacity: 0 }, 400, function() { $marker.remove(); cleanup(); });
            }
            else {
                cleanup();
            }
        }
    };

    window.markInvalidEmailSuccess = function($this) {
        ditchForm($this);
        $this.prev('.email').addClass('text-danger').children('a').contents().unwrap('a');
        $this.remove();
    };

    window.setupMapStyleSuccess = function($this) {
        window.location.reload();
    };

    window.feedbackSuccess = function($this, response) {
        $this.parents('.modal').modal('hide');
    };

});


// @license-end
