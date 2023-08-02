// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/scripts.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


// A bit of UI magic even before the DOM is loaded
document.getElementsByTagName('html')[0].className += ' js-enabled ';

$(document).ready(function() {

    // Antispam and fallback for unhandled mail links
    function openMailtoPopover($mailLink, htmlHasAddress, emailAddress) {
        var assistHtml = window.mailto_fallback && window.mailto_fallback[htmlHasAddress];
        assistHtml = (assistHtml || "").replace("[[email_address]]", emailAddress);
        if (!assistHtml && !htmlHasAddress) {
            assistHtml = emailAddress;
        }
        var popoverNode, $popover;
        $mailLink.on('inserted.bs.popover', function() {
            popoverNode = document.getElementById(this.getAttribute('aria-describedby'));
            $popover = $(popoverNode);
            if (navigator.clipboard) {
                var $copyButton = $(popoverNode.querySelector('.popover-content .email-copy-button'));
                $copyButton.removeClass('hidden').click(function() {
                    navigator.clipboard.writeText(emailAddress);
                });
            }
        });
        $mailLink.popover({
            trigger: "manual",
            placement: "top",
            html: true,
            sanitize: false,
            title: "",
            content: assistHtml,
        }).popover("show");
        var mailLinkBlurHandler = function(event) {
            if (!event.relatedTarget || !popoverNode.contains(event.relatedTarget)) {
                $mailLink.popover("destroy");
                $mailLink.off('blur', mailLinkBlurHandler);
            }
        };
        var popoverBlurHandler = function(event) {
            if (!event.relatedTarget ||
                    (event.relatedTarget != $mailLink[0] && !popoverNode.contains(event.relatedTarget))) {
                $mailLink.popover("destroy");
                $popover.off('focusout', popoverBlurHandler);
            }
        };
        $mailLink.on('blur', mailLinkBlurHandler);
        $popover.on('focusout', popoverBlurHandler);
        $mailLink.one('click', function() {
            $mailLink.off('blur', mailLinkBlurHandler);
            $popover.off('focusout', popoverBlurHandler);
        });
    }
    $('a[href^="mailto:"]').each(function() {
        var $mailLink = $(this);
        var href = $mailLink.attr('href').replace(" [cxe] ", "@");

        $mailLink.attr('href', href);
        $mailLink.html($mailLink.html().replace(" [cxe] ", "@"));

        if (!/iPhone;|iPad;/.test(navigator.userAgent) && this.getAttribute('data-nofallback') == null) {
            $mailLink.click(function() {
                $mailLink.tooltip("hide");
                var htmlHasAddress = $mailLink.html().indexOf("@") > 0;
                var t = setTimeout(function() {
                    // The browser did not respond after 500ms: expose the email address to the user
                    var assistHtml = window.mailto_fallback && window.mailto_fallback[htmlHasAddress];
                    if (typeof assistHtml === "undefined") {
                        var assistHtmlNode = document.createElement('div'),
                            fragment = '.mailto-address-' + (htmlHasAddress ? 'visible' : 'opaque');
                        $(assistHtmlNode).load('/fragment/mailto_fallback ' + fragment, function() {
                            window.mailto_fallback = window.mailto_fallback || {};
                            window.mailto_fallback[htmlHasAddress] = assistHtmlNode.innerHTML;
                            openMailtoPopover($mailLink, htmlHasAddress, href.replace('mailto:', ''));
                        });
                    }
                    else {
                        openMailtoPopover($mailLink, htmlHasAddress, href.replace('mailto:', ''));
                    }
                }, 500);
                $(window).blur(function() {
                    // The browser apparently responded: stop the timeout
                    clearTimeout(t);
                });
            });
        }
    });

    // Lazy load images
    $('.lazy').addClass('loaded');

    // Navigation skipping
    $('.navskip > a, a.scrolltop').click(function() {
        var targetName = this.getAttribute('href').substring(1);
        var targetElem = document.getElementById(targetName) || document.getElementsByName(targetName)[0];
        if (targetElem) {
            window.scroll(0, targetElem.getBoundingClientRect().top);
            targetElem.focus();
        }
        return false;
    });
    $('a.scrolltop').on('focus', function() { this.scrollIntoView(); });

    // Checkboxes with undefined value
    $('input[type="checkbox"][data-initial="None"]').prop('indeterminate', true);

    // Button hover
    +function() {
        var buttonSelector = '.btn[data-hover-text], .btn[data-hover-class]';
        var handlerIn = function() {
                var $this = $(this);
                if ($this.data('hover-text') && !$this.data('original-text')) {
                    var preserveWidth = $this.width();
                    $this.data('original-text', $this.html());
                    $this.text($this.data('hover-text')).width(preserveWidth);
                }
                if ($this.data('hover-class')) {
                    $this.addClass($this.data('hover-class'));
                }
        };
        var handlerOut = function() {
                var $this = $(this);
                if ($this.data('hover-text') && $this.data('original-text')) {
                    $this.html($this.data('original-text')).width("auto");
                    $this.data('original-text', "");
                }
                if ($this.data('hover-class')) {
                    $this.removeClass($this.data('hover-class'));
                }
        };
        $(buttonSelector)
            .hover(handlerIn, handlerOut)
            .focusin(handlerIn)
            .focusout(handlerOut);
    }();

    // Date picker widget for date fields
    if (typeof $().datepicker !== "undefined") {
        $('#id_blocked_from, #id_blocked_until').each(function () {
            var $input = $(this);
            var $toggler = $(document.createElement('span'));
            $toggler.addClass('form-control-feedback datepicker-btn-inline')
                    .attr('aria-hidden', "true")
                    .append($(document.createElement('span')).addClass('fa fa-regular fa-calendar'))
                    .click(function() { $input.datepicker("show"); });
            $input.after($toggler)
                  .parent().addClass('has-feedback');
            if ($input.hasClass('quick-form-control')) {
                var id_helper = this.id + '_descript';
                $input.data({dateShowOnFocus: false, dateKeyboardNavigation: false})
                      .siblings('.help-block').addClass('sr-only').attr('id', id_helper).end()
                      .attr('aria-describedby', id_helper);
            }
        });

        var fields_date = [$('#id_birth_date'),
                           $('#id_blocked_from, #id_blocked_until')];
        $.each(fields_date, function() { (this instanceof jQuery ? this : $(this)).each(function(index) {
            $(this).datepicker({
                format: "yyyy-mm-dd",
                maxViewMode: (this.id === 'id_birth_date' ? 3 : 2),
                weekStart: 1,
                startView: (this.id === 'id_birth_date' ? 2 : 1), // 0: month; 1: year; 2: decade;
                language: document.documentElement.lang,
            });
        }) });
    }

    // Technologies usage banner
    +function() {
        var bots = /bot|crawl|spider|slurp|bingpreview|pinterest|mail\.ru|facebookexternalhit|feedfetcher|feedburner/i;
        // see also https://ahrefs.com/images/robot/good-bots.jpg
        if (bots.test(navigator.userAgent)
                || Cookies.get('_consent')
                || /^\/(privacy|privateco)\//.test(document.location.pathname)
                || /^\/(agreement|kontrakto)\//.test(document.location.pathname))
            return;
        var $banner = $('#technologies-banner');
        $banner.show().delay(500).animate({ bottom: 0 }, 1500, 'linear')
               .find('.banner-close').click(function(event) {
                   event.preventDefault();
                   $(this).prop('disabled', true);
                   $banner.fadeOut();
                   Cookies.set(
                       '_consent',
                       typeof Date.prototype.toISOString !== "undefined" ? new Date().toISOString() : Date.now(),
                       { expires: 550 }
                   );
               });
    }();

    // Highlighting elements pointed at via the URL
    if (["fixed", "sticky"].indexOf($('header').css('position')) >= 0) {
        function repositionTarget(targetEl) {
            var $header = $('header'),
                positionDiff = targetEl.getBoundingClientRect().top - $header[0].getBoundingClientRect().bottom,
                margin = $header.outerHeight(true) - $header.outerHeight();
            if (typeof window.scrollBy === 'function') {
                if (positionDiff > margin * 1.5 || positionDiff <= 0) {
                    // Element is located far down... => Scroll the window to top with buffer of 10px.
                    // Element is located beneath the header... => Scroll the window to bottom with buffer of 10px.
                    window.scrollBy(0, positionDiff - 10);
                }
            }
            else {
                targetEl.scrollIntoView();
            }
        }
    }
    else {
        function repositionTarget(targetEl) {
            targetEl.scrollIntoView();
        }
    }
    $(':target').each(function() {
        var $targetEl = $(this);
        repositionTarget(this);
        setTimeout(function() {
            $targetEl.addClass('highlight');
        }, 1200);
        setTimeout(function() {
            $targetEl.removeClass('highlight');
        }, 2500);
    });

    // Profile picture magnifier
    if (typeof $().magnificPopup !== "undefined") {
        $('.profile-detail .owner .avatar img, a:has(#avatar-preview_id)').each(function() {
            var $magnifiedElem = $(this);
            $magnifiedElem.magnificPopup({
                type: "image",
                key: "profile-picture",
                closeOnContentClick: true,
                closeBtnInside: false,
                tLoading: gettext("Loading ▪ ▪ ▪"),
                tClose: gettext("Close"),
                disableOn: function() {
                    if ($magnifiedElem.is('[data-mfp-always]') || $magnifiedElem.has('[data-mfp-always]').length) {
                        return true;
                    }
                    else {
                        return $(window).width() <= 540;
                    }
                },
                image: {
                    tError: gettext("Cannot show the image. Please try again."),
                },
                zoom: {
                    enabled: true, duration: 400,
                },
                callbacks: {
                    open: function() {
                        var elem = this.st.el[0].parentElement;
                        if (elem.hasAttribute('data-content')) {
                            elem.setAttribute('data-content-backup', elem.getAttribute('data-content'));
                            elem.setAttribute('data-content', "");
                        }
                    },
                    close: function() {
                        var elem = this.st.el[0].parentElement;
                        if (elem.hasAttribute('data-content-backup')) {
                            elem.setAttribute('data-content', elem.getAttribute('data-content-backup'));
                            elem.removeAttribute('data-content-backup');
                        }
                    },
                }
            });
        });
    } // end magnifier setup

    // Broken profile images
    window.addEventListener('error', function(event) {
        var culprit = event.target, $culprit = $(event.target);
        if (culprit.tagName == 'IMG' && $culprit.parents('.avatar').length && !$culprit.data('erroring-url')) {
            $culprit.attr('data-erroring-url', culprit.src);
            culprit.src = $culprit.data('fallback') || '/static/img/image_not_available.png';
        }
    }, true);

    // AJAX Paginator
    if (typeof $().endlessPaginate !== "undefined") {
        $.endlessPaginate({
            paginateOnScroll: true,
            paginateOnScrollMargin: $('footer').outerHeight(true) + $('.endless_container').outerHeight(),
            onCompleted: function(context, fragment) {
                // The 'fragment' is just a String, not much can be done with it
                // TODO: place tab focus on the first added row
            }
        });
    }

    // Collapsing elements
    $('.top-notice:has(p.collapse)').each(function() {
        var $container = $(this);
        var noticeKey = 'advisory.ID.collapsed'.replace('ID', $container.data('id'));
        var $noticeContent = $container.children('p.collapse').first(),
            $noticeSwitch = $container.find('[data-toggle="collapse"]'),
            $noticeImage = $container.children('.top-notice-icon');
        var unfolder = function(event) {
            if (event.which == 13 || event.which == 32) {
                // Only the enter and space keys should be treated as action.
                event.preventDefault();
                $(this).click();
            }
        };
        var toggler = function(state) {
            $noticeSwitch.attr('aria-expanded', state);
            $noticeImage.toggleClass('content-collapsed', !state);
            $container.attr('tabindex', state ? null : 0)
                      .attr('data-toggle', state ? null : 'collapse')
                      .attr('data-target', state ? null : $noticeSwitch.attr('data-target'))
                      .attr('aria-expanded', state)
                      .css('cursor', state ? 'default' : 'pointer');
            if (state) {
                $noticeSwitch.show();
                $container.off('keypress', unfolder);
            }
            else {
                $noticeSwitch.hide();
                $container.on('keypress', unfolder);
            }
            window.setTimeout(function() { $noticeImage.removeClass('initial'); }, 100);
            window.localStorage && localStorage.setItem(noticeKey, !state);
        };
        $noticeContent.on('show.bs.collapse hide.bs.collapse',
                          function(event) { toggler(event.type == 'show') });
        if (window.localStorage && localStorage.getItem(noticeKey) == 'true') {
            $noticeImage.addClass('initial');
            $noticeContent.add($noticeContent.siblings('p.collapse')).collapse();
        }
        window.setTimeout(function() { $container.show(); }, 1750);
    });
    $('#family-panel-small').each(function() {
        var familyKey = 'place.ID.family-members.expanded';
        familyKey = familyKey.replace('ID', $('.place-detail').data('id'));
        var $familyPanel = $(this);
        var $familySwitch = $('[aria-controls='+this.id+']');
        var toggler = function(state) {
            $familySwitch.attr('aria-expanded', state).children('.fa').each(function() {
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
            window.localStorage && localStorage.setItem(familyKey, state);
        };
        $familyPanel.on('show.bs.collapse hide.bs.collapse',
                        function(event) { toggler(event.type == 'show') });
        if (window.localStorage && localStorage.getItem(familyKey) == 'true') {
            $familyPanel.addClass('in');
            $familySwitch.addClass('initial');
            toggler(true);
        }
    });
    $('#map-container').on('shown.bs.collapse hidden.bs.collapse', function() {
        window.mapObject && window.mapObject.resize();
        $('#map').css('visibility', $('#map').css('visibility') == 'hidden' ? 'visible' : 'hidden');
        $('[data-target="#map-container"]').toggleClass('active');
    });

    // Advanced search panel
    $('#advanced-filter-toggle').click(function(event) {
        $('[data-id="advanced-filter"]').collapse("show");
        event.preventDefault();
        document.querySelector('[data-id="advanced-filter"]').querySelector('input').focus();
    });
    $('[data-id="advanced-filter"]').on('shown.bs.collapse hidden.bs.collapse', function(event) {
        var toggle = document.getElementById('advanced-filter-toggle');
        if (toggle) {
            toggle.setAttribute('aria-expanded', event.type == 'shown');
        }
    });

    // Sortable lists (via drag-and-drop)
    if (typeof Sortable !== "undefined") {
        $('.phone-list').each(function() {
            var parentList = this, $parentList = $(parentList);
            Sortable.create(
                parentList,  // the raw DOM element.
                {
                    dataIdAttr: 'id',
                    handle: '.grabzone',
                    animation: 250,
                    setData: function(dataTransfer, el) {
                        dataTransfer.setDragImage($(el).find('.phone-number > .fa').get(0), 25, 25);
                        dataTransfer.setData('text/plain', $(el).find('.number').text());
                    },
                    onEnd: function(e) {
                        var priorities =
                                this.toArray()
                                .map(function(value) { return "onr=" + value; }).join("&");
                        $parentList.popover("destroy");
                        setTimeout(function() {
                            $.ajaxManualCall(
                                $parentList, $parentList.data('ajaxAction'), "POST",
                                priorities, "manual"
                            );
                            // timeout is required for the previous popover to finish
                            // destroying itself.
                        }, 250);
                    }
                }
            );
        }).click(function(event) {
            if (/\bset-priority-button\b/gi.test(event.target.className))
                return;
            $(this).popover("destroy");
        });
    }

    // Sortable lists (via manual buttons)
    $('.adjust-prio-switch')
    .click(function(event) {
        var $switch = $(this);
        $(this.dataset.listSelector + ' .priority-buttons').toggle();
        $(this.dataset.listSelector).toggleClass('prioritized-list');
        $switch.toggleClass('active')
               .attr('aria-pressed', function(_, attr) { return (attr == "true") ? false : true; })
               .attr('aria-expanded', function() { return this.getAttribute('aria-pressed'); });
        if ($switch.hasClass('set-kbd-focus')) {
            $(this.dataset.listSelector + ' .priority-buttons .set-priority-button')
                .first()
                .focus();
            $switch.removeClass('set-kbd-focus');
        }
    })
    .on('keypress', function(event) {
        if (event.which == 13 || event.which == 32) {
            $(this).toggleClass('set-kbd-focus');
        }
    });

    $('.set-priority-button')
    .click(function(event) {
        var $button = $(this),
            $row = $button.parents('.list-group-item'),
            $next = $row.next();
        if ($next.length == 0)
            return;
        var yDifference = Math.round($row.offset().top - $next.offset().top);
        $.each(
            [{row: $row, position: yDifference}, {row: $next, position: -yDifference}],
            function(_, relation) {
                relation.row.css({
                    "transition": "none",
                    "transform": "translate3d(0, " + relation.position + "px, 0)"
                });
            }
        );
        $row.children('.priority-buttons').toggle();
        $row.insertAfter($next);
        setTimeout(function() {
            $.each(
                [{row: $row, duration: 500}, {row: $next, duration: 250}],
                function(_, relation) {
                    relation.row.css({
                        "transition": "all " + relation.duration + "ms",
                        "transform": "translate3d(0, 0, 0)"
                    });
                }
            );
            setTimeout(function() {
                $row.children('.priority-buttons').toggle();
                if ($button.hasClass('set-kbd-focus')) {
                    $button.focus();
                }
            }, 250);
        }, 100);
        var priorities =
                $row.siblings().addBack()
                .map(function() { return "onr=" + this.id; }).get().join("&"),
            $parentList = $row.parents('.list-group');
        $parentList.popover("destroy");
        setTimeout(function() {
            $.ajaxManualCall($parentList, $parentList.data('ajaxAction'), "POST", priorities, "manual");
        }, 250);  // timeout is required for the previous popover to finish destroying itself.
    })
    .on('keypress', function(event) {
        if (event.which == 13) {
            // Only the enter key should be treated as action.
            event.preventDefault();
            $(this).addClass('set-kbd-focus').click();
        }
    });

    // Modal focus handling
    $(document).on('show.bs.modal', '.modal', function(event) {
        var $target = $(event.target);
        if (!$target.data('relatedSource') && event.relatedTarget) {
            $target.data('relatedSource', event.relatedTarget);
        }
    });
    $(document).on('hidden.bs.modal', '.modal', function(event) {
        var $target = $(event.target), sourceAttr = 'relatedSource';
        if ($target.data(sourceAttr)) {
            $target.data(sourceAttr).focus();
            $target.removeData(sourceAttr);
        }
    });

    // Host preferences popover setup
    if ($('#status-anchors_notification')[0]) {
        $('.anchor-notify').popover({
            trigger: "manual",
            html: true,
            content: $('#status-anchors_notification').data('content')
        });
    }

    enableTooltips();
});


// Bootstrap tooltips and popovers
function enableTooltips() {
    function realignTooltip(tip, elem) {
        var placement = getComputedStyle(elem).getPropertyValue('--tooltip-placement').trim()
                        || elem.getAttribute('data-placement') || 'top';
        var alt_placement = elem.getAttribute('data-alt-placement') == 'top' ? 'top' : 'bottom';
        if (placement == 'left' && elem.getBoundingClientRect().left < 85) {
            return alt_placement;
        }
        if (placement == 'right' && elem.getBoundingClientRect().right > window.outerWidth - 85) {
            return alt_placement;
        }
        return placement;
    }
    $('[data-toggle="tooltip"][title][data-title]').each(function() {
        this.setAttribute('data-simple-title', this.getAttribute('title'));
        this.removeAttribute('title');
    });
    $(document).tooltip({ selector: '[data-toggle="tooltip"]', placement: realignTooltip });
    $('body').tooltip({ selector: '[data-toggle="tooltip-lasting"]',
                        delay: { show: 0, hide: 2500 } });
    $('[data-toggle="popover"]').popover();
}


// Host preferences popover
function displayAnchorsNotification() {
    var $header = $('header'),
        $blockSmallDesc = $('.description-smallvp'),
        verticalOffset =
            $blockSmallDesc.offset().top - ($header.offset().top + $header.outerHeight(true));
    $('html, body').animate({ scrollTop: verticalOffset }, 500);

    var $origin = $('.anchor-notify');
    $origin.popover("show");
    var $notify = $origin.next('.popover');
    $origin.filter('.status').next('.popover').addClass('hidden-xs hidden-sm');

    $notify.animate({ opacity: 0.95 }, 600);
    window.setTimeout(function() {
        $notify.animate({ opacity: 0 }, 600, function() { $origin.popover("hide") });
    }, 5000);
}


// Utility function for determining Ctrl or Cmd keyboard combinations
$.Event.prototype.isCommandKey = function() {
    return (this.ctrlKey && !this.altKey) || this.metaKey;
}


// @license-end
