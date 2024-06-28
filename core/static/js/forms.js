// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/forms.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(function() {

    $(window).bind('load', function() {
        var flasher = $('.alert.flyover');
        flasher.addClass('in');
        if (!flasher.hasClass('no-out')) {
            window.setTimeout(function () { flasher.addClass('out') }, 4000);
        }
    });

    /* constraint validation and localization */
    if (typeof $().localConstraint === "undefined") {
        $.fn.extend({ localConstraint: {} });
    }
    if (!$().localConstraint.hasOwnProperty(document.documentElement.lang)) {
        $.fn.localConstraint[document.documentElement.lang] = [];
    }
    const formControlSelectors = [
        '.form-control', 'input[type="radio"]', 'input[type="checkbox"]', 'input[type="file"]',
    ].join();
    const formSubmitSelectors = [
        '#id_form_submit', '#id_form_submit_alt', '#id_form_submit_ext',
    ].join();

    function fieldValueValidationCallback(event, dontPropagate) {
        var $this = $(this);
        var constraint_failed = false;
        var errors = [];
        var localui = $().localConstraint[document.documentElement.lang];

        if (typeof this.setCustomValidity !== 'function')
            return;
        this.setCustomValidity("");

        if (this.validity.valueMissing) {
            var value_error = "";
            if ($this.attr('type') && localui.hasOwnProperty("valueMissing__"+$this.attr('type').toLowerCase()))
                value_error = localui["valueMissing__"+$this.attr('type').toLowerCase()];
            else if ($this.is('select') && $this.prop('multiple'))
                value_error = localui["valueMissing__select__multiple"];
            else if ($this.is('select'))
                value_error = localui["valueMissing__select"];
            else if (!$this.is(':file') && !$this.is(':radio'))
                value_error = localui["valueMissing"];
            errors.push($this.data('error-required') || value_error || this.validationMessage);
            constraint_failed = true;
        }
        if (this.validity.typeMismatch) {
            var value_error = "";
            value_error = localui["typeMismatch__"+$this.attr('type').toLowerCase()+($this.prop('multiple') ? "__multiple" : "")];
            errors.push(value_error || this.validationMessage);
            constraint_failed = true;
        }
        if (this.validity.patternMismatch) {
            var value_error = "", value_label = undefined;
            value_error = localui["patternMismatch"];
            if (value_error) {
                value_label = $('label[for="'+this.getAttribute('id')+'"]').text().trim().toLowerCase();
                value_error = value_error.replace("%(datum)s", value_label || localui["patternMismatch__default"]);
            }
            errors.push($this.data('error-pattern') || value_error || this.validationMessage);
            constraint_failed = true;
        }
        if (this.validity.tooLong || this.validity.tooShort) {
            var value_error = "";
            value_error = localui[this.validity.tooLong ? "tooLong" : "tooShort"];
            if (value_error) {
                value_error = value_error.replace("%(limit)s", $this.attr(this.validity.tooShort ? 'minlength' : 'maxlength'))
                                         .replace("%(len)s", $this.val().length);
            }
            errors.push(value_error || this.validationMessage);
            constraint_failed = true;
        }
        if (this.validity.rangeUnderflow || this.validity.rangeOverflow) {
            var error_type = "", value_error = "", is_date = false, is_time = false;
            is_date = $this.filter('[type=date], [type=month], [type=week]').length;
            is_time = $this.filter('[type=datetime], [type=datetime-local], [type=time]').length;
            error_type = $this.filter('[min][max]').length ? "minmax" : (this.validity.rangeUnderflow ? "min" : "max");
            value_error = localui[error_type+(is_date ? "__date" : (is_time ? "__time" : ""))];
            if (value_error) {
                value_error = value_error.replace("%(min)s", ($this.attr('min') || "").replace('T', ' '))
                                         .replace("%(max)s", ($this.attr('max') || "").replace('T', ' '));
            }
            errors.push(value_error || this.validationMessage);
            constraint_failed = true;
        }
        if (this.validity.stepMismatch) {
            var error_type = "", value_error = "";
            if ($this.is('[type="number"]')) {
                var elem_step = !isNaN($this.attr('step')) ? Number($this.attr('step')) : 1,
                    elem_min = !isNaN($this.attr('min')) ? Number($this.attr('min')) : undefined,
                    elem_max = !isNaN($this.attr('max')) ? Number($this.attr('max')) : undefined;
                var elem_step_base = elem_min || 0, value_low, value_high;
                value_low = $this.val() - ($this.val() - elem_step_base) % elem_step;
                value_high = value_low + elem_step * (elem_min === undefined && value_low < 0 ? -1 : 1);
                if (elem_min !== undefined && value_low < elem_min) {
                    value_low = elem_min;
                    value_high = value_low;
                }
                if (elem_max !== undefined && value_high > elem_max) {
                    if (value_low > elem_max)
                        value_low = elem_max - (elem_max - elem_step_base) % elem_step;
                    value_high = value_low;
                }
                value_error = localui["stepMismatch__number"+(value_low == value_high ? "__one" : "")];
                if (value_error) {
                    value_error = value_error.replace("%(low)s", value_low).replace("%(high)s", value_high);
                }
            }
            else {
                value_error = localui["stepMismatch"];
            }
            errors.push(value_error || this.validationMessage);
            constraint_failed = true;
        }
        if (this.validity.badInput) {
            var value_error = "";
            if ($this.attr('type'))
                value_error = localui["badInput__"+$this.attr('type').toLowerCase()];
            if (!value_error)
                value_error = localui["badInput"];
            errors.push(value_error || this.validationMessage);
            constraint_failed = true;
        }
        if ($this.is('input[type="file"]') && !isNaN($this.attr('maxlength'))) {
            var data = event.originalEvent.target.files[0];
            if (data && data.size > Number($this.attr('maxlength'))) {
                errors.push($this.data('error-maxlength') || localui["max__file"] || "The file provided by you is too large.");
                constraint_failed = true;
            }
        }
        if ($this.is('input[type="password"]') && $($this.data('coupling')).length == 1) {
            var data = $($this.data('coupling')).val();
            if ($this.val() && $this.val() != data) {
                errors.push(localui["valueMismatch__password"] || "The two password fields do not match.");
                constraint_failed = true;
            }
        }
        if ($this.attr('data-complex-validation-failed')) {
            errors.push($this.attr('data-complex-validation-failed'));
            constraint_failed = true;
        }

        if (constraint_failed) {
            this.setCustomValidity(errors.join("\n"));
            if (!$this.data('original-title')) {
                $this.data('original-title', $this.attr('title') || "[NULL]");
            }
            $this.attr('title', errors.join("\n"));
        }
        if (!constraint_failed) {
            this.setCustomValidity("");
            if ($this.data('original-title')) {
                $this.attr('title', $this.data('original-title') == "[NULL]" ? "" : $this.data('original-title'));
                $this.removeData('original-title');
                $this.removeAttr('original-title');
            }
            else if (!$this.attr('title')) {
                $this.attr('title', "");
            }
            // hide the server-side errors if value is valid, and unmark the
            // form group. skip for siblings in radio/checkbox groups.
            // this is not fullproof as client-side validation is weaker and
            // less complex than the server-side one.
            if (!dontPropagate) {
                var parent, container;
                if (this.type == 'checkbox' && !this.hasAttribute('data-parent-id')) {
                    parent = '.checkbox';
                    container = this.hasAttribute('data-extra-label') ? '.form-group' : '.checkbox';
                }
                else {
                    parent = '.controls';
                    container = '.form-group';
                }
                var $controlsBlock = $this.closest(parent),
                    fieldId = $this.data('parent-id') || this.id,
                    $siblings = $controlsBlock.closest(container).siblings('[id^="' + fieldId + '_option_"]');
                if ($siblings.length > 0) {
                    // support complex controls which consist of multiple groups.
                    $controlsBlock = $siblings.addBack().find(parent);
                }
                $controlsBlock.children('[id^="error_"][id$="' + fieldId + '"]').hide();
                $controlsBlock.closest(container).removeClass('has-error');
            }
        }

        if (($this.is('[type="radio"]') || $this.is('[type="checkbox"]')) && !dontPropagate) {
            // update similarly-named siblings (for radio/checkbox groups).
            $('[name="' + $this.attr('name') + '"]').not($this).each(function() {
                var sibling = this;
                $(sibling).triggerHandler('invalid', true);
            });
        }
    }
    function fieldValueValidationInit() {
        // initialize localized error messages for a field (and trigger validation).
        // the `invalid` event does not bubble and thus cannot be delegated.
        $(this).on('invalid', fieldValueValidationCallback);
        if (typeof this.checkValidity === 'function')
            this.checkValidity();
    }

    $('form')
    .on('blur', formControlSelectors, function(event, dontPropagate) {
        var $this = $(this), $form = $(this.form);
        $this.addClass('form-touched');
        if (($this.is('[type="radio"]') || $this.is('[type="checkbox"]')) && !dontPropagate) {
            // update similarly-named siblings (for radio/checkbox groups).
            $('[name="' + $this.attr('name') + '"]').not($this).each(function() {
                var sibling = this;
                $form.triggerHandler($.Event('focusout', {target: sibling}), [true]);
            });
        }
    })
    .on('input change', formControlSelectors, fieldValueValidationCallback)
    .find(formControlSelectors).each(fieldValueValidationInit).end()
    .on('click', formSubmitSelectors, function() {
        var $form = $(this.form);
        // mark the fields as visited on a submit button click and before the actual
        // form submission, which may not happen if some fields are invalid.
        Array.prototype.forEach.call(
            this.form.querySelectorAll(formControlSelectors),
            function(element) {
                $form.triggerHandler($.Event('focusout', {target: element}), [true]);
            }
        );
    });

    /* password fields coupling for client-side validation of correctly typed value */
    $('#id_password2').data('coupling', '#id_password1');
    $('#id_new_password2').data('coupling', '#id_new_password1');

    /* password field value toggling */
    const passwordToggleElements = document.querySelectorAll(
        'input[type="password"] + .password-toggle > button'
    );
    Array.prototype.forEach.call(passwordToggleElements, function(toggleButton) {
        var passwordField = toggleButton.parentElement.previousElementSibling,
            $toggleButton = $(toggleButton),
            toggleIconNode = toggleButton.querySelector('.fa'),
            $toggleTextNode = $(toggleButton.querySelector('.password-toggle-text'));
        var inactivityTimeoutID;

        function scheduleStateReset() {
            if (inactivityTimeoutID) {
                clearTimeout(inactivityTimeoutID);
            }
            inactivityTimeoutID = setTimeout(function() {
                $toggleButton.trigger('click', [false]);
                $toggleButton.prop('disabled', true);
            }, 1000 * 60 * 5);
        }

        $toggleButton.on('click', function(event, toggleState) {
            event.preventDefault();
            if (toggleState == undefined) {
                scheduleStateReset();
            }
            if (toggleState == $toggleButton.hasClass('active')) {
                // when we want to reveal the value but it is already shown,
                // or when we want to obscure the value but it is already hidden,
                // do nothing.
                return;
            }
            if ($toggleButton.prop('disabled')) {
                return;
            }
            $toggleButton.button("toggle");

            var currentFieldType = passwordField.getAttribute('type');
            passwordField.setAttribute('type', currentFieldType === "password" ? "text" : "password");

            var currentLabel = $toggleButton.attr('aria-label');
            $toggleButton.attr('aria-label', $toggleButton.data('aria-label-inactive'))
                         .data('aria-label-inactive', currentLabel);
            toggleIconNode.classList.toggle(toggleIconNode.getAttribute('data-icon-on'));
            toggleIconNode.classList.toggle(toggleIconNode.getAttribute('data-icon-off'));
            var currentText = $toggleTextNode.text();
            $toggleTextNode.text($toggleTextNode.data('label-inactive'))
                           .data('label-inactive', currentText);
        })

        $(passwordField)
        .on('keydown', function(event) {
            if (event.isCommandKey() && event.which == 32) {
                event.preventDefault();
                $toggleButton.trigger('click');
            };
        })
        .on('input', function() {
            $toggleButton.prop('disabled', false);
            scheduleStateReset();
        });
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
            rules: {
                scores: {
                    wordMaxLength: 2
                },
                activated: {
                    wordMaxLength: true
                }
            },
            ui: {
                bootstrap3: true,
                container: pwd_elements.parents('.controls').first()
                           .append('<div class="password-strength-meter"></div')
                           .end(),
                viewports: {
                    progress: '.password-strength-meter'
                },
                showVerdictsInsideProgressBar: true,
                progressBarMinWidth: 55,
                progressBarMinPercentage: 17,
                progressBarEmptyPercentage: 0,
                colorClasses: ['danger', 'danger', 'danger', 'warning', 'success', 'success']
            }
        });
        if (pwd_elements.length > 0) {
            var options = pwd_elements.data('pwstrength-bootstrap');
            var t_fallback = options.i18n.t;
            options.i18n.t = function (key) {
                var dict = $.fn.pwstrength.localui[document.documentElement.lang];
                if (key in dict)
                    return dict[key];
                return t_fallback(key);
            };
            $('#id_username, #id_email').on('input', function () {
                pwd_elements.pwstrength("forceUpdate");
            });
        }
    }

    /* dynamic updating of the country region form field */
    if (document.getElementById('id_country') && document.getElementById('id_state_province')) {
        $('#id_country').on('change', function() {
            var country = this.value;
            var nodeSubregion = document.getElementById('id_state_province'),
                currentValue, semanticRole;

            if (nodeSubregion.tagName == 'SELECT') {
                currentValue = nodeSubregion.selectedIndex > 0
                               ? nodeSubregion.options[nodeSubregion.selectedIndex].text : "";
            } else {
                currentValue = nodeSubregion.value;
            }
            semanticRole = nodeSubregion.getAttribute('autocomplete');

            $('#id_state_province_form_element').load(
                '/fragment/place_country_region_formfield' + (country ? '?country='+country : '')
                + ' #id_state_province_form_element > *',
                function(response, status) {
                    if (status == "error")
                        return;
                    nodeSubregion = document.getElementById('id_state_province');
                    if (semanticRole) {
                        nodeSubregion.setAttribute('autocomplete', semanticRole);
                    }
                    if (currentValue && nodeSubregion.tagName == 'INPUT') {
                        nodeSubregion.value = currentValue;
                    }
                    // set up a validation handler for this field.
                    fieldValueValidationInit.call(nodeSubregion);
                    // set up the rich selection control for this field.
                    $('select#' + nodeSubregion.id).chosen({
                        no_results_text: gettext("Nothing found for"),
                        disable_search_threshold: nodeSubregion.getAttribute('data-search-threshold'),
                    });
                }
            );
        });
    }

    /* dynamic display of names ordering (changes with user input) */
    var updatePersonNamesExample = function() {
        var nameF = $('#id_first_name').val().trim(),
            nameL = $('#id_last_name').val().trim(),
            labelFL = $('label:has(#id_names_inversed_1)'),
            labelLF = $('label:has(#id_names_inversed_2)');
        $.each(labelFL[0].childNodes, function() {
            if (this.nodeType == Node.TEXT_NODE && this.textContent.trim()) {
                if (nameF && nameL)
                    this.textContent = nameF + " " + nameL;
                else
                    this.textContent = labelFL.data('blank-label');
            }
        });
        $.each(labelLF[0].childNodes, function() {
            if (this.nodeType == Node.TEXT_NODE && this.textContent.trim()) {
                if (nameF && nameL)
                    this.textContent = nameL + " " + nameF;
                else
                    this.textContent = labelLF.data('blank-label');
            }
        });
    };
    if ($('#id_first_name, #id_last_name, input[type="radio"][id^="id_names_inversed"]').length != 4) {
        updatePersonNamesExample = function() {};
    }
    $('#id_first_name, #id_last_name').change(updatePersonNamesExample);

    +function() {
        $('ul.chosen-choices').addClass('form-control');
        $('.form-group .radio-inline').each(function() {
            $(this).data('blank-label', $(this).text().trim());
        });
        updatePersonNamesExample();
    }();

    /* verification for accidental birth date selection by the user */
    $('.own-profile-form #id_birth_date').change(function() {
        if (typeof this.validity !== "undefined" && this.validity.valid) {
            var birthDate = new Date(this.value);
            if (!isNaN(birthDate.getTime())) {
                var today = new Date(),
                    yearsDiff = Math.floor((today - birthDate) / (365.24 * 24 * 60 * 60 * 1000)),
                    warningId = 'error_age_' + this.id;
                if (yearsDiff < 6) {
                    var warningText = interpolate(
                        ngettext(
                            "Are you sure you are %(age)s year old?",
                            "Are you sure you are %(age)s years old?",
                            yearsDiff),
                        {'age': yearsDiff}, true);
                    var $warning = $(this).siblings('#' + warningId);
                    if ($warning.length == 0) {
                        $warning = $(document.createElement('span'))
                                   .attr('id', warningId)
                                   .addClass('help-block')
                                   .append('<span class="text-danger"></span>')
                                   .hide()
                                   .insertAfter(this);
                    }
                    $warning.animate({ opacity: 0.1 }, 400, function() {
                        $warning.children().text(warningText).end()
                                .show()
                                .animate({ opacity: 1 }, 600);
                    });
                }
                else {
                    $(this).siblings('#' + warningId).remove();
                }
            }
        }
    });

    /* fallback support for datalist */
    if (!('list' in document.createElement('input') &&
          Boolean(document.createElement('datalist') && window.HTMLDataListElement))) {
        var searchText = gettext("select one of the suggestions");
        $('.help-block[id^="hint_"]:contains("' + searchText + '")').each(function() {
            // for each help block, find the corresponding <input> if any.
            var pNode = this,
                inputId = (pNode.parentNode.getElementsByTagName('input')[0] || "").id;
            if (!inputId)
                return;
            // fetch the datalist fallback template and inject it after the form.
            var pageNode = document.querySelector('div[role="main"]');
            pageNode.appendChild(document.createElement('div'));
            $(pageNode.lastChild).load('/fragment/datalist_fallback', function(response, status) {
                if (status == "error") {
                    pageNode.removeChild(pageNode.lastChild);
                    return;
                }
                var $replacementModal = $(pageNode.lastChild.firstElementChild);
                // find the Text nodes that contain the magic string.
                var textNodes =
                    Array.prototype.filter.call(pNode.childNodes, function(node) {
                        return node.nodeType == 3  // text node
                               && node.data.indexOf(searchText) >= 0;
                    });
                // convert each Text node into an <a> element that pops a modal.
                textNodes.forEach(function(node) {
                    var linkTextNode = node.splitText(node.data.indexOf(searchText));
                    linkTextNode.splitText(searchText.length);
                    var linkNode =  document.createElement('a');
                    linkNode.setAttribute('href', "#retro");
                    linkNode.appendChild(linkTextNode.cloneNode());
                    linkTextNode.parentNode.replaceChild(linkNode, linkTextNode);
                    $(linkNode).click(function() {
                        $replacementModal.data('relatedSource', $(this));
                        $replacementModal.modal();
                    });
                });
                // prepare the contents of the modal.
                $replacementModal.attr(
                    'id',
                    $replacementModal.attr('id').replace("[[field_id]]", inputId));
                var dataitemTemplateNode =
                        $replacementModal[0].querySelector('.datalist-list').firstElementChild;
                Array.prototype.forEach.call(
                    document.querySelector('#'+inputId).nextElementSibling.children,
                    function(option) {
                        var dataitemNode = dataitemTemplateNode.cloneNode(true);
                        dataitemNode.querySelector('.datalist-item').innerText = option.value;
                        dataitemTemplateNode.parentNode.append(dataitemNode);
                    });
                dataitemTemplateNode.parentNode.removeChild(dataitemTemplateNode);
                $replacementModal.on('click', '.datalist-item', function() {
                    document.getElementById(inputId).value = this.innerText;
                    $replacementModal.modal("hide");
                    $('#'+inputId).trigger('input');
                });
            });
        });
    }

    /* for mass mail form */
    (function() {
        var frameElement = document.querySelector('iframe#massmail_preview');
        if (!frameElement)
            return;
        var frameContext = frameElement.contentDocument;
        frameContext.open();
        frameContext.write(frameElement.getAttribute('data-content'));
        frameContext.close();
        frameElement.removeAttribute('data-content');
        $(frameContext).ready(function() {
            $('#id_massmail-body').keyup(function() {
                $('#preview_body', frameContext).html(marked(this.value));
                var $preheader = $('#id_massmail-preheader');
                if (!$preheader.val().trim() || typeof $preheader.data('manual-input') === "undefined") {
                    $preheader.removeData('manual-input')
                              .val(this.value.replace(/(\r\n|\n|\r)/gm,' ').slice(0,99))
                              .data('previous-value', $preheader.val())
                              .keyup();
                }
            }).keyup();

            $.each(['heading', 'subject', 'preheader'], function(i, element) {
                $('#id_massmail-'+element).keyup(function(event) {
                    if (event && event.which) {
                        // manual usage of keyboard, not triggered via script.
                        var $this = $(this);
                        if (this.value != $this.data('previous-value')) {
                            $this.data('manual-input', true);
                            $this.data('previous-value', this.value);
                        }
                    }
                    $('#preview_'+element, element == 'heading' ? frameContext : null).html(this.value);
                }).keyup();
            });

            $('#id_massmail-categories').change(function() {
                $('#id_massmail-test_email').closest('.form-group').toggle(this.value === "test");
            }).change();
        });
    })();

    /* dynamic (collapsible) form area management */
    $('[id$="_form_element"].collapse').each(function() {
        var $switch = $('[aria-controls='+this.id+']');
        var toggler = function(state) {
            $switch.attr('aria-expanded', state).children('.fa').each(function() {
                var $this = $(this);
                var label = $this.attr('aria-label');
                $this.attr('aria-label', $this.data('aria-label-inactive'))
                     .data('aria-label-inactive', label);
                if (state)
                    $this.addClass('fa-rotate-90');
                else
                    $this.removeClass('fa-rotate-90');
                window.setTimeout(function() { $this.parent().removeClass('initial'); }, 100);
            });
        };
        $(this).on('show.bs.collapse hide.bs.collapse',
                   function(event) { toggler(event.type == 'show') });
    });

    /* form cancel button enhancement */
    $('#id_form_cancel').each(function() {
        this.setAttribute('data-default-href', this.getAttribute('href'));
        this.setAttribute('href', '#!');
    }).on('click', function(event) {
        event.preventDefault();
        history.go(-1);
    });
    /* form submit buttons double-submission prevention */
    $(formSubmitSelectors).closest('form')
    .on('submit', function(event) {
        // if client-side form validation fails, no 'submit' event will fire;
        // instead, the 'invalid' events will be raised. in addition, AJAX calls
        // do their own handling (overriding the default form behavior) and no
        // 'submit' event is raised either.
        if (event.originalEvent.submitter.id.indexOf('id_form_submit') == 0) {
            $(event.originalEvent.submitter).addClass('disabled')
                                            .prop('disabled', true)
                                            .attr('autocomplete', 'off');
            $(window).one('pagehide', function() {
                $(event.originalEvent.submitter).removeClass('disabled')
                                                .prop('disabled', false);
            });
        }
    });
    /* form submit/cancel keyboard shortcut key implementation */
    var actionButtonShortcuts = {length: 0};
    ['id_form_submit', 'id_form_submit_alt', 'id_form_cancel'].forEach(function(elementId) {
        var btnNode = document.getElementById(elementId);
        if (!btnNode)
            return;
        var shortcut = btnNode.getAttribute('data-kbdshortcut');
        if (!shortcut)
            return;
        actionButtonShortcuts[shortcut.charAt(0).toLowerCase()] = $('#'+elementId);
        actionButtonShortcuts.length++;
    });
    if (actionButtonShortcuts.length) {
        $(window).on('keydown', function(event) {
            if (event.isCommandKey()) {
                var pressedKey = String.fromCharCode(event.which).toLowerCase();
                if (actionButtonShortcuts[pressedKey] !== undefined) {
                    event.preventDefault();
                    actionButtonShortcuts[pressedKey].trigger('click');
                }
            };
        });
    }

});


// @license-end
