$(document).ready(function(){
    // Kontraŭspamo
    $("a[href^='mailto:']").each(function() {
        $(this).attr("href", $(this).attr("href").replace(" [cxe] ", "@"));
        $(this).html($(this).html().replace(" [cxe] ", "@"));
    });
});
