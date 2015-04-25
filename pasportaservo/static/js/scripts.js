$(document).ready(function(){
    // Kontraŭspamo
    $("a[href^='mailto:']").each(function() {
        $(this).attr("href", $(this).attr("href").replace(" [cxe] ", "@"));
        $(this).html($(this).html().replace(" [cxe] ", "@"));
    });

    // Close message
    $("a.close").click(function(e) {
        $(this).hide();
        $(this).parents(".message").slideUp();
        e.preventDefault();
    });

    // Lazy load images
    $(".lazy").addClass("loaded");
});
