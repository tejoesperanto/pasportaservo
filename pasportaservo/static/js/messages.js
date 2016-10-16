$(document).ready(function(){
    // Close message
    $('.close').click(function(e) {
        $(this).hide();
        $(this).parents('.message').slideUp();
        e.preventDefault();
    });

    // Close sticky message
    if (window.localStorage) {
        // Save sticky message class into localStorage when closing
        $(".close").click(function(e) {
            var stickyClass = $(this).parents('.message').attr("class").match(/sticky[\w-]*/).pop();
            localStorage.setItem(stickyClass, "hide");
        });

        // Remove sticky message if it has been already closed and saved in localStorage
        $('.message').each(function(i, el) {
            var stickyClass = $(el).attr("class").match(/sticky[\w-]*/).pop();
            if (localStorage.getItem(stickyClass)) {
                $("."+stickyClass).remove();
            }
        })
    }
});
