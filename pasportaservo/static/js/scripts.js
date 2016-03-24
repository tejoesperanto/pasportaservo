// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/scripts.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {
    // Kontraŭspamo
    $('a[href^="mailto:"]').each(function() {
        $(this).attr('href', $(this).attr('href').replace(" [cxe] ", "@"));
        $(this).html($(this).html().replace(" [cxe] ", "@"));
    });

    // Close message
    $('a.close').click(function(e) {
        $(this).hide();
        $(this).parents('.message').slideUp();
        e.preventDefault();
    });

    // Lazy load images
    $('.lazy').addClass('loaded');
    
    // Host preferences popover setup
    if ($('#status-anchors_notification')[0]) {
        $('.anchor-notify').popover({
            trigger: "manual",
            html: true,
            content: $('#status-anchors_notification').data("content") 
        });
    }
});


// Host preferences popover
function displayAnchorsNotification() {
    blockSmallDescription = $('.description-small');
    $('html, body').animate({ scrollTop: blockSmallDescription.offset().top - 10 }, 500);
    
    origin = $('.anchor-notify');
    origin.popover("show");
    notify = origin.next('.popover');
    origin.filter('.status').next('.popover').addClass('hidden-xs hidden-sm');
    
    notify.animate({ opacity: 0.95 }, 600);
    window.setTimeout(function() {
        notify.animate({ opacity: 0 }, 600, function() { origin.popover("hide") });
    }, 5000);
}


// @license-end
