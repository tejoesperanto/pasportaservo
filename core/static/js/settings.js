// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/settings.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {

    // Displays a suggestion to adjust the device or browser window when necessary.
    if (typeof screen !== "undefined") {
        var $matrix = $('.privacy-matrix-container table'),
            $matrixContainer = $matrix.parent();
        var $hintsBlock = $('.suggest-adjust-screen'),
            hints = {
                'turn-device': $hintsBlock.find('.turn-device'),
                'grow-window': $hintsBlock.find('.grow-window'),
                'slide-right': $hintsBlock.find('.slide-right'),
            };
        var conditions = {
                'turn-device': function() {
                    return screen.availWidth < 768 && screen.availWidth < screen.availHeight
                           && !('orientation' in window && Math.abs(window.orientation) == 90);
                },
                'grow-window': function() {
                    return window.outerWidth < screen.availWidth && window.outerWidth > 0 && window.innerWidth <= 768;
                },
                'slide-right': function() {
                    return $matrix.outerWidth() > $matrixContainer.innerWidth();
                },
        };

        function screenChangeHandler() {
            var shownHints = 0;
            for (var type in hints) {
                shownHints += didScreenConditionChange(hints[type], conditions[type]);
            }
            if (shownHints > 0) {
                $hintsBlock.show();
                $hintsBlock.find('.help-block.in').css('margin-bottom', '').last().css('margin-bottom', 0);
            }
            else {
                $hintsBlock.hide();
            }
        };
        /* handling both 'resize' and 'orientationchange' events is required, due to:
         *  •  iOS firing resize events, but the window orientation being incorrect when the event is handled
         *  •  Android supporting also pop-out windows and split screen (essentially creating a window)
         *  •  the desktop browsers not firing and not supporting any events related to the window orientation
         */
        window.addEventListener('resize', screenChangeHandler);
        window.addEventListener('orientationchange', screenChangeHandler);
        try {
            window.dispatchEvent(new Event('resize'));
        }
        catch (e) {
            var event = document.createEvent('UIEvent');
            event.initEvent('resize', false, false);
            window.dispatchEvent(event);
        }
    }
    function didScreenConditionChange($hint, condition) {
        if (condition()) {
            $hint.addClass('in');
            return 1;
        }
        else {
            $hint.removeClass('in');
            return 0;
        }
    }

    // Automatically checks or unchecks the paired toggles.
    function updatePairedPrivacyToggle(event) {
        var onlyForCondition = event.data;
        if (onlyForCondition === true || onlyForCondition === false) {
            if (onlyForCondition !== $(this).prop('checked'))
                return;
        }
        var other_id = this.id.match(/(id_publish-\d+-visible_online_)[a-z_-]+/);
        var query = '[id^=' + other_id[1] + ']';
        $(query).not(this)
            .prop('checked', $(this).prop('checked'))
            .bootstrapToggle("update", true, true);
    }
    $('[data-tied=True]').change(updatePairedPrivacyToggle);
    $('[id$=-visible_online_public]:not([data-tied=True])').change(true,  $.proxy(updatePairedPrivacyToggle));
    $('[id$=-visible_online_authed]:not([data-tied=True])').change(false, $.proxy(updatePairedPrivacyToggle));

    // Displays users authorized to view full place details.
    // Supports multiple panels on the same page.
    $('.authorized-list.panel').collapse({toggle: false});
    $('.authorized-list.switch').click(function(event) {
        var $target = $($(this).data('target'));
        var $otherPanels = $('.authorized-list.panel.collapse.in').not($target);
        var continuationHandler = function() {
            var toggleQName = "panel-toggle";
            if ($otherPanels.length > 0) {
                $otherPanels.off("hidden.bs.collapse", continuationHandler);
                $target.delay(200, toggleQName);
            }
            $target.queue(toggleQName, function(next) {
                $target.collapse("toggle");
                next();
            })
            .dequeue(toggleQName);
        };
        event.preventDefault();
        if ($otherPanels.length > 0)
            $otherPanels.on("hidden.bs.collapse", continuationHandler).collapse("hide");
        else
            continuationHandler();
    });

    // Places the 'setting saved' indicator near the checkbox.
    $('.optinout-success').first().appendTo(
        $('#id_public_listing, #id_site_analytics_consent').parent()
    ).css({ "visibility": "hidden", "display": "" });
    // Places the 'more info' link into the checkbox' help block.
    $('#analytics_more_link').each(function() {
        $(this).closest('form')
               .find('#id_site_analytics_consent')
               .closest('.form-group')
               .find('.help-block')
               .append(" ", this);
    });

    window.updateVisibilitySetup = function($this) {
        $this.closest('form').find('#id_dirty').val($this.get(0).name);
    };

    window.updateVisibilityResult = function($this, response) {
        if (response.result === true) {
            var $marker = $this.closest('td').find('.visibility-success');
            var $notify = $(document.createElement('span')).addClass('sr-only')
                          .text($marker.data('notification'));
            flashSuccessIndicator(
                $marker,
                function() { $marker.html($notify); },
                function() { $notify.remove(); }
            );
        }
        else {
            updatePrivacyFailure($this);
        }
    };

    window.updatePrivacyResult = function($this, response) {
        if (response.result === true) {
            var $marker = $this.parent().find('.optinout-success');
            var $notify = $marker.find('.notification');
            flashSuccessIndicator(
                $marker,
                function() { $notify.text($marker.data('notification')); },
                function() { $notify.text(""); }
            );
        }
        else {
            updatePrivacyFailure($this);
        }
    }

    function flashSuccessIndicator($marker, action_pre, action_post) {
        $marker.delay(250)
               .css({ "visibility": "visible", "opacity": 0 });
        if (typeof action_pre === "function") {
            action_pre();
        }
        $marker.animate({ opacity: 1 }, 400)
               .delay(2000)
               .animate({ opacity: 0 }, 400, function() {
                    $(this).css("visibility", "hidden");
                    if (typeof action_post === "function") {
                        action_post();
                    }
               });
        return $marker;
    }

    window.updatePrivacyFailure = function($this) {
        $this.closest('form').data('unsaved', true);
        var unsavedNotifier = function(event) {
            var notification = gettext("You have not yet saved the privacy settings.");
            var $notifyEl = $(document.createElement('span'))
                .addClass('alert alert-info flyover in')
                .text(notification)
                // Timeouts are disabled by modern browsers in 'beforeunload' handlers
                // to prevent rogue websites from locking users in. Any operations
                // after the delay will be executed only if the user stays on the page.
                .delay(500)
                .queue(function(next) { $(this).addClass('out'); next(); })
                .delay(1000).queue(function() { $(this).remove(); });
            $('#page').prepend($notifyEl);
            event.originalEvent.returnValue = notification;
            return notification;
        };
        var submitButton = $this.closest('form').find('#id_privacy_form_submit');
        if (!arguments.callee.willAlert) {
            $(window).on('beforeunload', unsavedNotifier);
            submitButton.one('click', function() {
                $(window).off('beforeunload', unsavedNotifier);
            });
            arguments.callee.willAlert = true;
            submitButton
                .delay(150).queue(function(next) { $(this).addClass('btn-warning'); next(); })
                .delay(650).queue(function(next) { $(this).removeClass('btn-warning'); next(); })
                .delay(350).queue(function(next) { $(this).addClass('btn-warning'); next(); })
                .delay(650).queue(function(next) { $(this).removeClass('btn-warning'); next(); });
        }
    };

});


// @license-end
