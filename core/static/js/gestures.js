// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/gestures.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


(function ($) {
    const gestureSwipeOff = function (callback) {
        let $el = $(this), sourceEl = this;
        let moveStartX = undefined, moveStartY = undefined;
        let origOffset = $el.offset().left;

        // Init
        let settings = {
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
        let $container =
            $(document.createElement('div'))
                .css({
                    'position': 'relative',
                    'overflow': 'hidden',
                    'width': '100%',
                    'border-style': 'dashed',
                    'border-width': '0px 1px',
                    'border-left-color': 'transparent',
                    'border-right-color': 'transparent',
                    'margin-bottom': $el.css('margin-bottom'),
                })
                .insertBefore($el).append($el)
                .parent().css('overflow', 'hidden').end();
        $el.css({
            'position': 'relative',
            'margin-bottom': 0,
        });
        if (window.matchMedia('(any-pointer: coarse)').matches) {
            $el.css({'touch-action': 'pan-y pinch-zoom'});
        }

        // Cancelation
        sourceEl.cancelSwipe = function(e) {
            if (moveStartX === undefined || moveStartY === undefined)
                return;
            moveStartX = moveStartY = undefined;
            $el.animate(
                { left: 0 }, function() {
                    $container.css('border-left-color', 'transparent');
                    $container.css('border-right-color', 'transparent');
                });
            if (e.originalEvent.pointerId) {
                sourceEl.releasePointerCapture(e.originalEvent.pointerId);
            }
        };
        // Reset
        sourceEl.resetSwipe = function() {
            $el.css({ left: 0 });
            $container.css({ left: 0 });
        };

        $el
        .on(settings.touchOnly ? 'touchstart' : 'pointerdown', function(e) {
            moveStartX = e.pageX != undefined ? e.pageX : e.originalEvent.touches[0].pageX;
            moveStartY = e.pageY != undefined ? e.pageY : e.originalEvent.touches[0].pageY;
            if (e.originalEvent.pointerId) {
                sourceEl.setPointerCapture(e.originalEvent.pointerId);
            }
        })
        .on(settings.touchOnly ? 'touchmove' : 'pointermove', function(e) {
            if (moveStartX === undefined || moveStartY === undefined)
                return;

            let currentX = e.pageX != undefined ? e.pageX : e.originalEvent.touches[0].pageX,
                currentY = e.pageY != undefined ? e.pageY : e.originalEvent.touches[0].pageY;
            let diffX = currentX - moveStartX,
                diffY = Math.abs(currentY - moveStartY);
            if (diffY > (settings.touchOnly ? 60 : 30)) {
                // Vertical movement discards the swiping off.
                sourceEl.cancelSwipe(e);
                return;
            }
            $container.css(
                'border-right-color',
                diffX > 0 ? settings.borderRightColor : 'transparent');
            $container.css(
                'border-left-color',
                diffX > 0 ? 'transparent' : settings.borderLeftColor);
            $el.animate({ left: diffX }, 0);

            // If threshold is exceeded (to the left or to the right),
            // deem the swiping off as confirmed.
            if (Math.abs(diffX) > 200 && settings.canCompleteSwipe.call(sourceEl, diffX)) {
                let targetX;
                moveStartX = moveStartY = undefined;
                if (diffX > 0) {
                    targetX = $(window).width() - origOffset + 50;
                }
                else {
                    targetX = -origOffset - $el.width() - 50;
                }
                $container.animate({ left: targetX }, function() {
                    $container.css('border-width', 0);
                    function completionHandler() {
                        settings.swipeCompleted.call(sourceEl, diffX);
                        $el.trigger("off.swipe.ps");
                    }
                    if (settings.collapse) {
                        $el.slideUp(completionHandler);
                    }
                    else {
                        completionHandler();
                    }
                });
            }
        })
        .on(settings.touchOnly ?
                'touchend touchcancel' :
                'pointerup pointercancel',
            e => sourceEl.cancelSwipe(e)
        );
    };

    $.fn.swipeoff = function (callback) {
        $(this).each(function() { gestureSwipeOff.call(this, callback); });
    }
}(jQuery));


// @license-end
