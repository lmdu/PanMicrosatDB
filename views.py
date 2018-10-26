from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections
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

		seqid = int(request.POST.get('sequence', 0))
		begin = int(request.POST.get('begin', 0))
		end = int(request.POST.get('end', 0))
		motif = request.POST.get('motif')
		smotif = request.POST.get('smotif')
		ssrtype = int(request.POST.get('ssrtype', 0))
		repsign = request.POST.get('repsign')
		repeats = int(request.POST.get('repeats', 0))
		lensign = request.POST.get('lensign')
		ssrlen = int(request.POST.get('ssrlen', 0))

		data = []
		with in_database(db_config):
			#total = int(SSRStat.objects.get(name='ssr_count').val)
			ssrs = SSR.objects.all()
			if seqid:
				ssrs = ssrs.filter(sequence=seqid)

			if begin and end:
				ssrs = ssrs.filter(start__gte=begin, end__lte=end)

			if motif:
				ssrs = ssrs.filter(motif=motif)

			if smotif:
				ssrs = ssrs.filter(standard_motif=smotif)

			if ssrtype:
				ssrs = ssrs.filter(ssr_type=ssrtype)

			if repeats:
				if repsign == 'gt':
					ssrs = ssrs.filter(repeats__gt=repeats)
				elif repsign == 'gte':
					ssrs = ssrs.filter(repeats__gte=repeats)
				elif repsign == 'eq':
					ssrs = ssrs.filter(repeats=repeats)
				elif repsign == 'lt':
					ssrs = ssrs.filter(repeats__lt=repeats)
				elif repsign == 'lte':
					ssrs = ssrs.filter(repeats__lte=repeats)

			if ssrlen:
				if lensign == 'gt':
					ssrs = ssrs.filter(length__gt=ssrlen)
				elif lensign == 'gte':
					ssrs = ssrs.filter(length__gte=ssrlen)
				elif lensign == 'eq':
					ssrs = ssrs.filter(length=ssrlen)
				elif lensign == 'lt':
					ssrs = ssrs.filter(length__lt=ssrlen)
				elif lensign == 'lte':
					ssrs = ssrs.filter(length__lte=ssrlen)


			total = ssrs.count()

			for ssr in ssrs[start:start+length]:
				data.append((ssr.id, ssr.sequence.accession, ssr.sequence.name, ssr.start, ssr.end, ssr.motif, ssr.standard_motif, ssr.get_ssr_type_display(), ssr.repeats, ssr.length))

		return JsonResponse({
			'draw': draw,
			'recordsTotal': total,
			'recordsFiltered': total,
			'data': data
		})

@csrf_exempt
def get_seq_id(request):
	if request.method == 'POST':
		term = request.POST.get('term', '')
		page = int(request.POST.get('page', 1))
		rows = int(request.POST.get('rows', 10))
		label = request.POST.get('label')

		db_config = {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': 'GCF_000001735.4.db'
		}
		with in_database(db_config) as db:
			offset = (page-1)*rows
			if term:
				#total = Sequence.objects.filter(accession__contains=term).count()
				#seqs = Sequence.objects.filter(accession__contains=term)[offset:offset+rows]
				term = '{}*'.format(term)
				with connections[db.unique_db_id].cursor() as cursor:
					cursor.execute("SELECT COUNT(*) FROM search WHERE search MATCH %s", (term,))
					total = cursor.fetchone()[0]
				
				seqs = Search.objects.raw("SELECT rowid,name,accession FROM search WHERE search MATCH %s LIMIT %s,%s", (term, offset, rows))

				if label == 'accession':
					data = [{'id': seq.rowid, 'text': seq.accession} for seq in seqs]
				elif label == 'name':
					data = [{'id': seq.rowid, 'text': seq.name} for seq in seqs]
			else:
				total = int(SSRStat.objects.get(name='seq_count').val)
				seqs = Sequence.objects.all()[offset:offset+rows]

				if label == 'accession':
					data = [{'id': seq.id, 'text': seq.accession} for seq in seqs]
				elif label == 'name':
					data = [{'id': seq.id, 'text': seq.name} for seq in seqs]

		return JsonResponse({'results': data, 'total': total})

@csrf_exempt
def get_seq_flank(request):
	if request.method == 'POST':
		ssr_id = int(request.POST.get('ssrid'))
		
		db_config = {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': 'GCF_000001735.4.db'
		}
		with in_database(db_config):
			ssr = SSR.objects.get(id=ssr_id)
			ssrmeta = SSRMeta.objects.get(id=ssr_id)
		
		ssr_seq = "".join([ssr.motif]*ssr.repeats)
		bases = []

		for b in ssrmeta.left_flank:
			bases.append('<span class="{0}">{0}<span>'.format(b))

		bases.append('<strong>')
		for b in ssr_seq:
			bases.append('<span class="{0}">{0}<span>'.format(b))
		bases.append('</strong>')

		for b in ssrmeta.right_flank:
			bases.append('<span class="{0}">{0}<span>'.format(b))

		return JsonResponse({'seq': "".join(bases)})

