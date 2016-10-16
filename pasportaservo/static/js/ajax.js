$(document).ready(function(){
  $('.ajax').click(function(e){
    e.preventDefault();
    $this = $(this)
    $this.addClass('disabled');
    $.ajax({
        type: 'POST',
        url: $this.attr('href'),
        data: {'csrfmiddlewaretoken': $this.data('csrf')},
        dataType: 'json',
        success: function(response) {
            // TODO: Make it generic
            $this.html($this.html().replace($this.text().trim(), ''));
            $this.attr('title', $this.data('title-success'));
            $this.removeClass('ajax');
        },
        error: function() {
            $this.removeClass('disabled');
        }
    });
  })
});