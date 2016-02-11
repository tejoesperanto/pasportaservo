$(function() {

    if (typeof $().datepicker !== "undefined") {
        $('#id_birth_date').datepicker({
            format: "yyyy-mm-dd",
            weekStart: 1,
            startView: 2, // 0: month; 1: year; 2: decade;
            language: "eo"
        });
    }

    $(window).bind("load", function() {
        $('ul.chosen-choices').addClass('form-control');
        flasher = $('.alert.flyover');
        flasher.addClass('in');
        if (!flasher.hasClass('no-out')) {
            window.setTimeout(function () { flasher.addClass('out') }, 4000);
        }
    });
    
    /* for mass mail form */
    $('#id_body').keyup(function() {
        $('#antauvido').html(marked($(this).val()));
    }).keyup();

    $('#id_categories').change(function() {
        if ($(this).val() === "test") {
            $('#id_test_email').closest('.form-group').show();
        } else {
            $('#id_test_email').closest('.form-group').hide();
        }
    }).change();

    /* form submit/cancel keyboard shortcut key implementation */
    if ($('#id_form_submit, #id_form_cancel').is(function() { return $(this).data('kbdshortcut') })) {
        shortcutY = ($('#id_form_submit').data('kbdshortcut') || '\0').charAt(0).toLowerCase();
        shortcutN = ($('#id_form_cancel').data('kbdshortcut') || '\0').charAt(0).toLowerCase();
        $(window).bind("keydown", function(event) {
            if ((event.ctrlKey && !event.altKey) || event.metaKey) {
                pressedKey = String.fromCharCode(event.which).toLowerCase()
                if (pressedKey === shortcutY) {
                    event.preventDefault();
                    $('#id_form_submit').click();
                }
                if (pressedKey === shortcutN) {
                    event.preventDefault();
                    $('#id_form_cancel').click();
                }
            };
        });
    }
    
});
