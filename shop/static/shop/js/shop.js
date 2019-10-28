// @source: https://github.com/tejo-esperanto/pasportaservo/blob/master/shop/static/shop/js/shop.js
// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL v3


$(function() {
    // Parses a float from the DOM
    var parse = function(txt) { return parseFloat(txt.replace(',', '.')) };
    // Formats a float for the DOM
    var format = function(num) { return num.toFixed(2).toString().replace('.', ',') };
    // Initiates the state of the Amount button group. See amountRange.
    var initButtonArray = function(amount) {
        // TODO: the positional selectors :last and :nth will be removed in jQuery 4.0
        if (amount >= 10) {
            $('.btn-group label:last').button('toggle');
        }
        else {
            $('.btn-group label:nth-of-type('+ (amount || 0) +')').button('toggle');
        }
    };

    // The Knockout View model:
    function CalculationViewModel() {
        var self = this;
        this.productLowPrice = parse($("#product-low-price").text());
        this.productPrice =    parse($("#product-price").text());
        this.shipping =        parse($("#shipping").text());
        this.amountRange = [1,2,3,4,5,6,7,8,9,'+']
        this.inBook = ko.observable($('#id_in_book').prop('checked'));
        this.productAmount = ko.observable($('#id_amount').val());
        this.productAmountComp = ko.computed(function() {
            //console.log(this.inBook());
            return this.inBook() ? this.productAmount() -1 : this.productAmount()
        }, this);
        this.supportInput = ko.observable($('#id_support').val());
        // Parsed Float field
        this.support = ko.computed(function() {
            var supportAmount = parse(this.supportInput());
            return isNaN(supportAmount) ? 0 : Math.max(supportAmount, 0);
        }, this);
        this.hasTejoDiscount = ko.observable(false);
        this.productSum = ko.computed(function() {
            return this.productAmountComp() * this.productPrice;
        }, this);
        this.productTotal = ko.computed(function() {
            return this.inBook() ? this.productLowPrice + this.productSum() : this.productSum()
        }, this);
        // Discount of one third (~33%) after 3 or more articles
        this.volumeDiscount = ko.computed(function() {
            if (this.productAmount() < 3) { return 0 }
            else { return this.productTotal() / 3 }
        }, this);
        // Discount of 10% offered by UEA/TEJO twice a year
        this.tejoDiscount = ko.computed(function() {
            if (!this.hasTejoDiscount()) { return 0 }
            else { return (this.productTotal() - this.volumeDiscount()) / 10 }
        }, this);

        this.total = ko.computed(function() {
            return this.productTotal()
                 - this.volumeDiscount()
                 - this.tejoDiscount()
                 + this.support()
                 + this.shipping
        }, this);

        this.amountClicked = function(item) {
            if (item === '+') { self.productAmount(15) }
            else { self.productAmount(item) }
        }

        // Formats the values for displaying
        this.productSumFmt = ko.computed(function() {
            return format(this.productSum())
        }, this);
        this.volumeDiscountFmt = ko.computed(function() {
            return format(-this.volumeDiscount())
        }, this);
        this.tejoDiscountFmt = ko.computed(function() {
            return format(-this.tejoDiscount())
        }, this);
        this.totalFmt = ko.computed(function() {
            return format(this.total())
        }, this);
    }

    // Activates knockout.js
    ko.applyBindings(new CalculationViewModel());

    initButtonArray($("#id_amount").val());
    $("#id_amount").on('change input', function() { initButtonArray($(this).val()); });
});


// @license-end
