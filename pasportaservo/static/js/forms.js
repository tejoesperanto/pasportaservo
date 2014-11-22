$(function() {

    $('#id_birth_date').datepicker({
        format: "yyyy-mm-dd",
        weekStart: 1,
        startView: 2, // 0: month; 1: year; 2: decade;
        language: "eo"
    });

    $(window).bind("load", function() {
        $('ul.chosen-choices').addClass("form-control");
    });
});
