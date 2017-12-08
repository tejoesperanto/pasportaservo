// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/settings.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {

    // Automatically checks or unchecks the paired toggles
    function updatePairedPrivacyToggle(event) {
        var onlyForCondition = event.data;
        if (onlyForCondition === true || onlyForCondition === false)
            if (onlyForCondition !== $(this).prop('checked'))
                return;
        var other_id = this.id.match(/(id_form-\d+-visible_online_)[a-z_-]+/);
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

    window.updateVisibilitySetup = function($this) {
        $this.closest('form').find('#id_dirty').val($this.get(0).name);
    };

    window.updateVisibilityResult = function($this, response) {
        if (response.result === true) {
            var $marker = $this.closest('td').find('.visibility-success');
            var $notify = $(document.createElement('span')).addClass('sr-only')
                          .text($marker.data('notification'));
            $marker.delay(500)
                   .css({ "visibility": "visible", "opacity": 0 })
                   .html($notify)
                   .animate({ opacity: 1 }, 400)
                   .delay(2000)
                   .animate({ opacity: 0 }, 400, function() {
                       $(this).css("visibility", "hidden");
                       $notify.remove();
                   });
        }
        else {
            updateVisibilityFailure($this);
        }
    };

    window.updateVisibilityFailure = function($this) {
        $this.closest('form').data('unsaved', true);
        var unsavedNotifier = function(event) {
            var notification = (document.documentElement.lang == "eo")
                               ? "Vi ne jam konservis la agordojn de privateco."
                               : "You have not yet saved the privacy settings.";
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
        var submitButton = $this.closest('form').find('#id_vis_form_submit');
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
