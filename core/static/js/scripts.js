// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/scripts.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {
    // Kontraŭspamo
    $('a[href^="mailto:"]').each(function() {
        $(this).attr('href', $(this).attr('href').replace(" [cxe] ", "@"));
        $(this).html($(this).html().replace(" [cxe] ", "@"));
    });

    // Lazy load images
    $('.lazy').addClass('loaded');

    // Button hover
    $('.btn').hover(function() {
        var $this = $(this);
        $this.data('original-text', $this.text());
        if ($this.data('hover-text')) {
            $this.text($this.data('hover-text'));
        }
        if ($this.data('hover-class')) {
            $this.addClass($this.data('hover-class'));
        }
    }, function() {
        var $this = $(this);
        if ($this.data('hover-text') && $this.data('original-text')) {
            $this.text($this.data('original-text'));
        }
        if ($this.data('hover-class')) {
            $this.removeClass($this.data('hover-class'));
        }
    });

    // Date picker widget for date fields
    if (typeof $().datepicker !== "undefined") {
        $('#id_blocked_from, #id_blocked_until').each(function () {
            var $input = $(this);
            var $toggler = $(document.createElement('span'));
            $toggler.addClass("glyphicon glyphicon-calendar form-control-feedback datepicker-btn-inline")
                    .attr('aria-hidden', "true")
                    .click(function() { $input.datepicker("show"); });
            $input.after($toggler)
                  .data({dateShowOnFocus: false, dateKeyboardNavigation: false})
                  .parent().addClass("has-feedback");
        });

        var fields_date = [$('#id_birth_date'),
                           $('#id_blocked_from, #id_blocked_until')];
        $.each(fields_date, function() { (this instanceof jQuery ? this : $(this)).each(function(index) {
            $(this).datepicker({
                format: "yyyy-mm-dd",
                maxViewMode: (this.id === 'id_birth_date' ? 3 : 2),
                weekStart: 1,
                startView: (this.id === 'id_birth_date' ? 2 : 1), // 0: month; 1: year; 2: decade;
                language: document.documentElement.lang,
            });
        }) });
    }

    // Image links with custom highlighting
    +function() {
        var set_highlight = function() {
            var src = $(this).children('img').attr('src');
            if (src.match(/-hl\.[a-z]+$/))
                return;
            $(this).children('img').attr('src', src.replace(/\.([a-z]+)$/, "-hl.$1"));
        };
        var del_highlight = function() {
            var src = $(this).children('img').attr('src');
            $(this).children('img').attr('src', src.replace(/-hl\.([a-z]+)$/, ".$1"));
        };
        $('.highlight-custom').hover(set_highlight, del_highlight);
        $('.highlight-custom').focus(set_highlight);
        $('.highlight-custom').blur( del_highlight);
    }();

    // Profile picture magnifier
    if (typeof $().magnificPopup !== "undefined") {
        $('.owner-avatar img, a:has(#avatar-preview_id)').each(function() {
            var $magnifiedElem = $(this);
            $magnifiedElem.magnificPopup({
                type: "image",
                key: "profile-picture",
                closeOnContentClick: true,
                closeBtnInside: false,
                tLoading: (document.documentElement.lang == "eo") ? "Ŝargata ▪ ▪ ▪" : "Loading ▪ ▪ ▪",
                tClose: (document.documentElement.lang == "eo") ? "Fermi" : "Close",
                disableOn: function() {
                    if ($magnifiedElem.is('[data-mfp-always]') || $magnifiedElem.has('[data-mfp-always]').length) {
                        return true;
                    }
                    else {
                        return $(window).width() <= 540;
                    }
                },
                image: {
                    tError: (document.documentElement.lang == "eo") ?
                            "Ne eblas montri la bildon. Bv provu denove." : "Cannot show the image. Please try again.",
                },
                zoom: {
                    enabled: true, duration: 400,
                },
                callbacks: {
                    open: function() {
                        var elem = this.st.el[0].parentElement;
                        if (elem.hasAttribute('data-content')) {
                            elem.setAttribute('data-content-backup', elem.getAttribute('data-content'));
                            elem.setAttribute('data-content', "");
                        }
                    },
                    close: function() {
                        var elem = this.st.el[0].parentElement;
                        if (elem.hasAttribute('data-content-backup')) {
                            elem.setAttribute('data-content', elem.getAttribute('data-content-backup'));
                            elem.removeAttribute('data-content-backup');
                        }
                    },
                }
            });
        });
    } // end magnifier setup

    // Host preferences popover setup
    if ($('#status-anchors_notification')[0]) {
        $('.anchor-notify').popover({
            trigger: "manual",
            html: true,
            content: $('#status-anchors_notification').data("content")
        });
    }

    // Bootstrap tooltips and popovers
    $('[data-toggle=tooltip]').tooltip({html: true});
    $('[data-toggle=tooltip-lasting]').tooltip({ delay: { show: 0, hide: 2000, } });
    $('[data-toggle=popover]').popover();
});


// Host preferences popover
function displayAnchorsNotification() {
    var blockSmallDescription = $('.description-small');
    $('html, body').animate({ scrollTop: blockSmallDescription.offset().top - 10 }, 500);

    var origin = $('.anchor-notify');
    origin.popover("show");
    var notify = origin.next('.popover');
    origin.filter('.status').next('.popover').addClass('hidden-xs hidden-sm');

    notify.animate({ opacity: 0.95 }, 600);
    window.setTimeout(function() {
        notify.animate({ opacity: 0 }, 600, function() { origin.popover("hide") });
    }, 5000);
}


// @license-end
