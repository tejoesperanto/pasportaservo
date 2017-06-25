// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/gestures.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


(function ($) {
    $.fn.swipeoff = function (callback) {
        var $el = $(this);
        var moveStartX = undefined, moveStartY = undefined;
        var origOffset = $el.offset().left;

        // Setup
        var $container =
            $(document.createElement('div'))
                .css({'position': 'relative', 'overflow': 'hidden',
                      'border-style': 'dotted', 'border-width': 0,
                      'border-left-color': $el.css('border-left-color'),
                      'border-right-color': $el.css('border-right-color'),
                      'margin-bottom': $el.css('margin-bottom')})
                .insertBefore($el).append($el);
        $el.css({'position': 'relative', 'margin-bottom': 0});

        // Cancelation
        var cancelSwipe = function() {
            if (moveStartX === undefined || moveStartY === undefined)
                return;
            moveStartX = undefined; moveStartY = undefined;
            $el.animate({ left: 0 }, function() { $container.css('border-width', 0); });
        };

        $el
        .on('pointerdown', function(e) {
            moveStartX = e.pageX;
            moveStartY = e.pageY;
        })
        .on('pointermove', function(e) {
            if (moveStartX === undefined || moveStartY === undefined)
                return;

            var diffX = e.pageX - moveStartX,
                diffY = Math.abs(e.pageY - moveStartY);
            if (diffY > 30) {
                // Vertical movement discards the swiping off
                cancelSwipe();
                return;
            }
            if (diffX > 0)
                $container.css('border-right-width', '1px');
            else
                $container.css('border-left-width', '1px');
            $el.animate({ left: diffX }, 0);

            // If threshold exceeded (to the left or to the right),
            // deem the swiping off as confirmed
            if (Math.abs(diffX) > 200) {
                var targetX;
                moveStartX = undefined; moveStartY = undefined;
                if (diffX > 0)
                    targetX = $(window).width() - origOffset + 50;
                else
                    targetX = -origOffset - $el.width() - 50;
                $container.animate({ left: targetX }, function() {
                    $container.css('border-width', 0);
                    $el.slideUp(function() {
                        if ($.isFunction(callback))
                            callback();
                        $el.trigger("off.swipe.ps");
                    });
                });
            }
        })
        .on('pointerup pointerout pointercancel', cancelSwipe);
    };
}(jQuery));


// @license-end
