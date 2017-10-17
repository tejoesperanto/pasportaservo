// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/gestures.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


(function ($) {
    var gestureSwipeOff = function (callback) {
        var $el = $(this), sourceEl = this;
        var moveStartX = undefined, moveStartY = undefined;
        var origOffset = $el.offset().left;

        // Init
        var settings = {
            swipeCompleted: function() {},
            canCompleteSwipe: function() { return true; },
            borderLeftColor: $el.css('border-left-color'),
            borderRightColor: $el.css('border-right-color'),
            collapse: true,
            touchOnly: false
        };
        if ($.isPlainObject(callback)) {
            $.extend(true, settings, callback);
        }
        if ($.isFunction(callback)) {
            settings.swipeCompleted = callback;
        }

        // Setup
        var $container =
            $(document.createElement('div'))
                .css({'position': 'relative', 'overflow': 'hidden',
                      'width': '100%',
                      'border-style': 'dotted', 'border-width': 0,
                      'border-left-color': settings.borderLeftColor,
                      'border-right-color': settings.borderRightColor,
                      'margin-bottom': $el.css('margin-bottom')})
                .insertBefore($el).append($el)
                .parent().css('overflow', 'hidden').end();
        $el.css({'position': 'relative', 'margin-bottom': 0});

        // Cancelation
        sourceEl.cancelSwipe = function() {
            if (moveStartX === undefined || moveStartY === undefined)
                return;
            moveStartX = undefined; moveStartY = undefined;
            $el.animate({ left: 0 }, function() { $container.css('border-width', 0); });
        };
        // Reset
        sourceEl.resetSwipe = function() {
            $el.css({ left: 0 });
            $container.css({ left: 0 });
        };

        $el
        .on(settings.touchOnly ? 'touchstart' : 'pointerdown', function(e) {
            moveStartX = e.pageX;
            moveStartY = e.pageY;
        })
        .on(settings.touchOnly ? 'touchmove' : 'pointermove', function(e) {
            if (moveStartX === undefined || moveStartY === undefined)
                return;

            var diffX = e.pageX - moveStartX,
                diffY = Math.abs(e.pageY - moveStartY);
            if (diffY > 30) {
                // Vertical movement discards the swiping off
                sourceEl.cancelSwipe();
                return;
            }
            $container.css('border-right-width', diffX > 0 ? '1px' : '0');
            $container.css('border-left-width', diffX > 0 ? '0' : '1px');
            $el.animate({ left: diffX }, 0);

            // If threshold exceeded (to the left or to the right),
            // deem the swiping off as confirmed
            if (Math.abs(diffX) > 200 && settings.canCompleteSwipe.call(sourceEl, diffX)) {
                var targetX;
                moveStartX = undefined; moveStartY = undefined;
                if (diffX > 0)
                    targetX = $(window).width() - origOffset + 50;
                else
                    targetX = -origOffset - $el.width() - 50;
                $container.animate({ left: targetX }, function() {
                    $container.css('border-width', 0);
                    var completionHandler = function() {
                        settings.swipeCompleted.call(sourceEl, diffX);
                        $el.trigger("off.swipe.ps");
                    };
                    if (settings.collapse)
                        $el.slideUp(completionHandler);
                    else
                        completionHandler();
                });
            }
        })
        .on(settings.touchOnly ?
                'touchend touchcancel' :
                'pointerup pointerout pointercancel',
            sourceEl.cancelSwipe);
    };

    $.fn.swipeoff = function (callback) {
        $(this).each(function() { gestureSwipeOff.call(this, callback); });
    }
}(jQuery));


// @license-end
