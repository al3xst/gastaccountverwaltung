$(function() {
    $('#btnSignUp').click(function() {
		$.ajax({
			url: '/sign_up',
			data: $('form').serialize(),
			type: 'POST',
			success: function(response) {
				rspsn = JSON.parse(response);
				console.log(rspsn);

				$("#error").html('<div class="alert-success"> &nbsp; '+rspsn.message+'<br>Für einen neuen Gastaccount laden sie bitte diese Seite neu </div>' );
				$('#btnSignUp').prop('disabled', true);
			},
			error: function(error) {
			    rspns = JSON.parse(error.responseText);
				$("#error").html('<div class="alert alert-danger"> &nbsp; '+rspns.error+' </div>');
                console.log(error);
                console.log(rspns);
				if(rspns.actn == "disableBtn")
				    $('#btnSignUp').prop('disabled', true);
			}
		});
	});
});
