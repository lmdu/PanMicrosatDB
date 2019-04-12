$(document).ready(function(){

$('.dropdown-toggle').dropdown();

//species and group select
$('#kingdom-select').select2({
	width: '100%',
	theme: 'classic',
	ajax: {
		url: "category",
		type: 'POST',
		dataType: 'json',
		delay: 250,
		data: function(params){
			return {
				term: params.term,
				page: params.page,
				parent: 0,
				level: 1,
				rows: 10
			};
		},
		processResults: function(data, params){
			params.page = params.page || 1;

			return {
				results: data.results,
				pagination: {
					more: (params.page*10) < data.total
				}
			};
		},
		cache: true,
		minimumInputLength: 1
	},
});

$('#group-select').select2({
	width: '100%',
	theme: 'classic',
	ajax: {
		url: "category",
		type: 'POST',
		dataType: 'json',
		delay: 250,
		data: function(params){
			return {
				term: params.term,
				page: params.page,
				parent: $('#kingdom-select').val() || 0,
				level: 2,
				rows: 10
			};
		},
		processResults: function(data, params){
			params.page = params.page || 1;

			return {
				results: data.results,
				pagination: {
					more: (params.page*10) < data.total
				}
			};
		},
		cache: true,
		minimumInputLength: 1
	},
});

$('#subgroup-select').select2({
	width: '100%',
	theme: 'classic',
	ajax: {
		url: "category",
		type: 'POST',
		dataType: 'json',
		delay: 250,
		data: function(params){
			return {
				term: params.term,
				page: params.page,
				parent: $('#group-select').val() || 0,
				level: 3,
				rows: 10
			};
		},
		processResults: function(data, params){
			params.page = params.page || 1;

			return {
				results: data.results,
				pagination: {
					more: (params.page*10) < data.total
				}
			};
		},
		cache: true,
		minimumInputLength: 1
	},
});

$('#species-select').select2({
	width: '100%',
	theme: 'classic',
	ajax: {
		url: "category",
		type: 'POST',
		dataType: 'json',
		delay: 250,
		data: function(params){
			return {
				term: params.term,
				page: params.page,
				parent: $('#subgroup-select').val() || 0,
				level: 4,
				rows: 10
			};
		},
		processResults: function(data, params){
			params.page = params.page || 1;

			return {
				results: data.results,
				pagination: {
					more: (params.page*10) < data.total
				}
			};
		},
		cache: true,
		minimumInputLength: 1
	},
});


$('#view-option-select').select2({
	width: '100%',
	theme: 'classic'
});

$('#view-option-select').on('change', function(){
	var option = $('#view-option-select').val();
	var species = $('#species-select').val();

	if(option==='summary'){
		$.redirect('species', {species: species}, 'POST');
	}else if(option === 'ssr'){
		$.redirect('browse', {species: species}, 'POST');
	}else{
		$.redirect('compound', {species: species}, 'POST');
	}
});

$('#kingdom-select').on('change', function(){
	$('#group-select').val(0).trigger('change');
	$('#subgroup-select').val(0).trigger('change');
	$('#species-select').val(0).trigger('change');
});
$('#group-select').on('change', function(){
	$('#subgroup-select').val(0).trigger('change');
	$('#species-select').val(0).trigger('change');
});
$('#subgroup-select').on('change', function(){
	$('#species-select').val(0).trigger('change');
});
$('#species-select').on('change', function(){
	if(parseInt($('#species-select').val())){
		$('#view-option-select').prop('disabled', false);
	}else{
		$('#view-option-select').prop('disabled', true);
	}
});

//highchart global setting
Highcharts.setOptions({
	credits: {
		enabled: false
	}
});

});