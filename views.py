from django.shortcuts import render
from django.http import JsonResponse
from dynamic_db_router import in_database
from django.views.decorators.csrf import csrf_exempt

from .models import *

# Create your views here.
def index(request):
	return render(request, 'panmicrosatdb/index.html')

@csrf_exempt
def browse(request):
	if request.method == 'GET':
		return render(request, 'panmicrosatdb/browse.html')
	
	elif request.method == 'POST':
		db_config = {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': 'GCF_000001735.4.db'
		}
		start = int(request.POST.get('start'))
		length = int(request.POST.get('length'))
		draw = int(request.POST.get('draw'))

		print(start, length)

		data = []
		with in_database(db_config):
			total = int(SSRStat.objects.get(name='ssr_count').val)
			for ssr in SSR.objects.all()[start:start+length]:
				data.append((ssr.id, ssr.sequence.accession, ssr.sequence.name, ssr.start, ssr.end, ssr.motif, ssr.standard_motif, ssr.get_ssr_type_display(), ssr.repeats, ssr.length))
		
		print(len(data))

		return JsonResponse({
			'draw': draw,
			'recordsTotal': total,
			'recordsFiltered': total,
			'data': data
		})

@csrf_exempt
def get_sequence_accession(request):
	if request.method == 'POST':
		print(request.POST)
		term = request.POST.get('term')
		db_config = {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': 'GCF_000001735.4.db'
		}
		with in_database(db_config):
			if not term:
				seqs = Sequence.objects.all()[:5]
			else:
				seqs = Sequence.objects.filter(accession__contains=term)[:5]
			data = [{'id': seq.id, 'text': seq.accession} for seq in seqs]

		return JsonResponse({'results': data, 'pagination': {'more': True}})
		

