// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/blog/static/js/supervisors.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {

    var $gotoNext = $('#id_next_post'),
        $gotoPrev = $('#id_prev_post');

    function navigateBlog($whereto) {
        window.location = $whereto.attr('href') + "#T";
    }

    $('article').swipeoff({
        canCompleteSwipe : function(direction) {
            return (direction > 0 && $gotoPrev.length == 1)
                   || (direction < 0 && $gotoNext.length == 1);
        },
        swipeCompleted : function(direction) {
            var $element = $(this),
                $whereto = direction > 0 ? $gotoPrev : $gotoNext;
            var navQName = "blog-nav";
            $whereto.queue(navQName, function(next) {
                        $whereto.addClass('btn-success');
                        next();
                    })
                    .delay(500, navQName)
                    .queue(navQName, function(next) {
                        $whereto.removeClass('btn-success');
                        $element[0].resetSwipe();
                        navigateBlog($whereto);
                        next();
                    })
                    .dequeue(navQName);
        },
        borderLeftColor: "#eee",
        borderRightColor: "#eee",
        collapse: false,
        touchOnly: true
    });

    $(window).bind('keydown', function(event) {
        if (event.isCommandKey()) {
            var $whereto = event.keyCode == 39 ? $gotoNext :
                          (event.keyCode == 37 ? $gotoPrev : undefined);
            if ($whereto !== undefined && $whereto.length == 1) {
                event.preventDefault();
                navigateBlog($whereto);
            }
        };
    });

});


// @license-end
