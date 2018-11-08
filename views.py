from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections
from dynamic_db_router import in_database
from django.views.decorators.csrf import csrf_exempt

from .models import *

import json

# Create your views here.
def index(request):
	return render(request, 'panmicrosatdb/index.html')

def overview(request):
	return render(request, 'panmicrosatdb/overview.html')

def species(request, sid):
	return render(request, 'panmicrosatdb/species.html')

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
		max_repeats = int(request.POST.get('maxrep', 0))
		lensign = request.POST.get('lensign')
		ssrlen = int(request.POST.get('ssrlen', 0))
		max_ssrlen = int(request.POST.get('maxlen', 0))
		location = int(request.POST.get('location', 0))

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
				elif repsign == 'in':
					ssrs = ssrs.filter(repeats__range=(repeats, max_repeats))

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
				elif lensign == 'in':
					ssrs = ssrs.filter(length__range=(ssrlen, max_ssrlen))

			if location:
				ssrs = ssrs.filter(ssrannot__location=location)


			total = ssrs.count()

			#order by
			colidx = request.POST.get('order[0][column]')
			colname = request.POST.get('columns[{}][name]'.format(colidx))
			sortdir = request.POST.get('order[0][dir]')

			if sortdir == 'asc':
				ssrs = ssrs.order_by(colname)
			else:
				ssrs = ssrs.order_by('-{}'.format(colname))

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

			info = """
			<table class="table table-bordered table-sm">
				<tr><th>Location</th><td colspan="3">{}:{}-{}</td></tr>
				<tr><th>Motif</th><td>{}</td><th>Repeats</th><td>{}</td></tr>
				<tr><th>Type</th><td>{}</td><th>Length</th><td>{}</td></tr>
			</table>
			""".format(ssr.sequence.name, ssr.start, ssr.end, ssr.motif,
			 ssr.repeats, ssr.get_ssr_type_display(), ssr.length)

		left_seq = "".join(['<span class="N">{0}</span>'.format(b) for b in ssrmeta.left_flank])
		right_seq = "".join(['<span class="N">{0}</span>'.format(b) for b in ssrmeta.right_flank])
		ssr_seq = "".join(['<span class="{0}">{0}</span>'.format(b) for b in "".join([ssr.motif]*ssr.repeats)])

		return JsonResponse({'seq': '{}{}{}{}'.format(info, left_seq, ssr_seq, right_seq)})

