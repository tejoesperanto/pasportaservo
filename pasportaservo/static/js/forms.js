// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/pasportaservo/static/js/forms.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(function() {

    if (typeof $().datepicker !== "undefined") {
        $('#id_birth_date').datepicker({
            format: "yyyy-mm-dd",
            weekStart: 1,
            startView: 2, // 0: month; 1: year; 2: decade;
            language: document.documentElement.lang
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

    /* password strength meter for password input fields (registration, password change) */
    if (typeof $().pwstrength !== "undefined") {
        $.fn.pwstrength.localui = $.fn.pwstrength.localui || {};
        if (! $.fn.pwstrength.localui.hasOwnProperty(document.documentElement.lang))
            $.fn.pwstrength.localui[document.documentElement.lang] = [];
        
        var pwd_elements = $('#id_password1, #id_new_password1');
        pwd_elements.pwstrength({
            common: {
                zxcvbn: true,
                userInputs: ['#id_username', '#id_email', '#id_old_password'],
                zxcvbnTerms: ["pasporta", "servo", "saluton", "esperanto", "esperantist", "zamenhof", "pasvorto", "sekret"]
            },
            ui: {
                showVerdictsInsideProgressBar: true,
                progressBarMinPercentage: 15,
                progressBarEmptyPercentage: 0,
                colorClasses: ['danger', 'danger', 'danger', 'warning', 'success', 'success']
            }
        });
        if (pwd_elements.length > 0) {
            var options = pwd_elements.data("pwstrength-bootstrap");
            var t_fallback = options.i18n.t;
            options.i18n.t = function (key) {
                var dict = $.fn.pwstrength.localui[document.documentElement.lang];
                if (key in dict)
                    return dict[key];
                return t_fallback(key);
            };
            $('#id_username, #id_email').on("input", function () {
                pwd_elements.pwstrength("forceUpdate");
            });
        }
    }

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


// @license-end
