// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/core/static/js/supervisors.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(document).ready(function() {

    // Load and store remembered country list tab
    window.switchActiveTab = function (shouldLoadRememberedTab) {
        if (window.localStorage) {
            var tabKey = 'supervisors.by-country.active-tab';
            if (shouldLoadRememberedTab) {
                var storedTab = localStorage.getItem(tabKey);
                if (storedTab && /^#countries-[a-z_-]+$/.test(storedTab)) {
                    $('[data-toggle="tab"][href="'+storedTab+'"]').tab("show");
                }
            }
            $('ul.nav-tabs > li > [data-toggle="tab"]').on('shown.bs.tab', function(e) {
                var activeTab = $(e.target).attr('href');
                localStorage.setItem(tabKey, activeTab);
            });
        }
    };

    // Load and store the collapse status for the "supervisor tasks" box
    // Uses the browser's built-in local storage
    if (window.localStorage) {
        var tasksKey = 'supervisors.tasks.collapsed';
        var $tasksSwitch = $('#tasks-header .switch');
        $('#tasks').on('hide.bs.collapse', function() {
            localStorage.setItem(tasksKey, true);
            $tasksSwitch.html("[&#43;]");
        }).on('show.bs.collapse', function() {
            localStorage.setItem(tasksKey, false);
            $tasksSwitch.html("[&#8722;]");
        });
        if (localStorage.getItem(tasksKey) == 'true') {
            $('#tasks').removeClass('in');
            $tasksSwitch.html("[&#43;]");
        }
        else {
            $tasksSwitch.html("[&#8722;]");
        }
    }
    else {
        var $tasksSwitch = $('#tasks-header .switch');
        $tasksSwitch.parents('[data-toggle="collapse"]')
            .removeAttr('data-toggle data-target aria-controls');
        $tasksSwitch.remove();
    }

    // Load and store the hide status for "supervisors wanted" box
    // Requires the Cookies and the Gestures plugins
    if (Cookies.get('lo-off')) {
        $('#supervisors-wanted').hide();
    }
    function storeHideStatus() {
        Cookies.set('lo-off', new Date().getTime() / 1000, { expires: 90 });
    };
    $('#supervisors-wanted .close').on('click', function() {
        storeHideStatus();
        $(this).parent().slideUp();
    }).parent().swipeoff(storeHideStatus);

    $('.country-code').on('click', function(e) {
        var $this = $(this);
        $this.data('qqn', e.timeStamp - $this.data('qqt') < 1000 ? $this.data('qqn')+1 : 0);
        $this.data('qqt', e.timeStamp);
        if ($this.data('qqn') == 5) {
            $this.children('span, img').toggle(300);
        }
    });

});


// @license-end
