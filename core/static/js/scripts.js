// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/scripts.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {
    // Kontraŭspamo
    $('a[href^="mailto:"]').each(function() {
        $(this).attr('href', $(this).attr('href').replace(" [cxe] ", "@"));
        $(this).html($(this).html().replace(" [cxe] ", "@"));
    });

    // Lazy load images
    $('.lazy').addClass('loaded');

    // Checkboxes with undefined value
    $('input[type="checkbox"][data-initial="None"]').prop('indeterminate', true);

    // Button hover
    $('.btn').hover(function() {
        var $this = $(this);
        $this.data('original-text', $this.text());
        if ($this.data('hover-text')) {
            var preserveWidth = $this.width();
            $this.text($this.data('hover-text')).width(preserveWidth);
        }
        if ($this.data('hover-class')) {
            $this.addClass($this.data('hover-class'));
        }
    }, function() {
        var $this = $(this);
        if ($this.data('hover-text') && $this.data('original-text')) {
            $this.text($this.data('original-text')).width("auto");
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
            $toggler.addClass('fa fa-calendar form-control-feedback datepicker-btn-inline')
                    .attr('aria-hidden', "true")
                    .click(function() { $input.datepicker("show"); });
            var id_helper = this.id + '_descript';
            $input.siblings('.help-block').addClass('sr-only').attr('id', id_helper).end()
                  .attr('aria-describedby', id_helper)
                  .after($toggler)
                  .data({dateShowOnFocus: false, dateKeyboardNavigation: false})
                  .parent().addClass('has-feedback');
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

    // Technologies usage banner
    +function() {
        var bots = /bot|crawl|spider|slurp|bingpreview|pinterest|mail\.ru|facebookexternalhit|feedfetcher|feedburner/i;
        // see also https://ahrefs.com/images/robot/good-bots.jpg
        if (bots.test(navigator.userAgent)
                || Cookies.get('_consent')
                || /^\/(privacy|privateco)\//.test(document.location.pathname))
            return;
        var $banner = $('#technologies-banner');
        $banner.show().delay(500).animate({ bottom: 0 }, 1500, 'linear')
               .find('.banner-close').click(function(event) {
                   event.preventDefault();
                   $(this).prop('disabled', true);
                   $banner.fadeOut();
                   Cookies.set(
                       '_consent',
                       typeof Date.prototype.toISOString !== "undefined" ? new Date().toISOString() : Date.now(),
                       { expires: 550 }
                   );
               });
    }();

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
        $('.profile-detail .owner .avatar img, a:has(#avatar-preview_id)').each(function() {
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

    // Collapsing elements
    $('#family-panel-small').each(function() {
        var familyKey = 'place.ID.family-members.expanded';
        familyKey = familyKey.replace('ID', $('.place-detail').data('id'));
        var $familyPanel = $(this);
        var $familySwitch = $('[aria-controls='+this.id+']');
        var toggler = function(state) {
            $familySwitch.attr('aria-expanded', state).children('.fa').each(function() {
                var $this = $(this);
                var label = $this.attr('aria-label');
                $this.attr('aria-label', $this.data('aria-label-inactive'))
                     .data('aria-label-inactive', label);
                if (state)
                    $this.addClass('fa-rotate-90');
                else
                    $this.removeClass('fa-rotate-90');
                window.setTimeout(function() { $this.parent().removeClass('initial'); }, 100);
            });
            window.localStorage && localStorage.setItem(familyKey, state);
        };
        $familyPanel.on('hide.bs.collapse', function() { toggler(false); })
                    .on('show.bs.collapse', function() { toggler(true); });
        if (window.localStorage && localStorage.getItem(familyKey) == 'true') {
            $familyPanel.addClass('in');
            $familySwitch.addClass('initial');
            toggler(true);
        }
    });

    // Host preferences popover setup
    if ($('#status-anchors_notification')[0]) {
        $('.anchor-notify').popover({
            trigger: "manual",
            html: true,
            content: $('#status-anchors_notification').data('content')
        });
    }

    // Bootstrap tooltips and popovers
    $('[data-toggle=tooltip]').tooltip();
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


// Utility function for determining Ctrl or Cmd keyboard combinations
$.Event.prototype.isCommandKey = function() {
    return (this.ctrlKey && !this.altKey) || this.metaKey;
}


// @license-end
