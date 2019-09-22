// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/messages.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {
    // Close message
    $('.message .close').click(function(e) {
        $(this).hide();
        $(this).parents('.message').slideUp();
        e.preventDefault();
    });

    +function() {
        var messages = $('.message.eminent');
        if (!messages.length)
            return;
        var msgbox = messages.filter('.error').first();
        if (!msgbox.length)
            msgbox = messages.filter('.warning').first();
        if (!msgbox.length)
            msgbox = messages.filter('.info').first();
        if (!msgbox.length)
            msgbox = messages.filter('.success').first();
        messages.first().before(messages.clone(true).removeClass('eminent'));
        messages.not(msgbox).hide();
        window.setTimeout(function () { msgbox.addClass('out') }, 4000);
        window.setTimeout(function () { messages.children('.close').click() }, 6000);
    }();

    // Close sticky message
    if (window.localStorage) {
        // Save sticky message class into localStorage when closing
        $('.message .close').click(function() {
            var messageClasses = $(this).parents('.message').attr('class').match(/sticky[\w-]*/);
            if (messageClasses) {
                var stickyClass = messageClasses.pop();
                localStorage.setItem(stickyClass, "hide");
            }
        });

        // Remove sticky message if it has been already closed and saved in localStorage
        $('.message').each(function() {
            var messageClasses = $(this).attr('class').match(/sticky[\w-]*/);
            if (messageClasses) {
                var stickyClass = messageClasses.pop();
                if (localStorage.getItem(stickyClass)) {
                    $('.'+stickyClass).remove();
                }
            }
        });
    }
});


// @license-end
