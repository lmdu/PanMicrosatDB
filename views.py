import re
import json

from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.db import connections
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string

from .router import in_database
from .models import *
from .utils import *
from .plots import *
from .tasks import *
from .display import *
from .downloader import *

# Create your views here.
def index(request):
	return render(request, 'psmd/index.html')

@csrf_exempt
def category(request):
	if request.method == 'POST':
		term = request.POST.get('term', '')
		page = int(request.POST.get('page', 1))
		rows = int(request.POST.get('rows', 10))
		level = int(request.POST.get('level'))
		parent = int(request.POST.get('parent'))
		offset = (page-1)*rows

		if level == 4:
			gs = Genome.objects.filter(category=parent)
			if term:
				gs = gs.filter(species_name__icontains=term)

			total = gs.count()
			data = [{'id': g.id, 'text': g.species_name}for g in gs[offset:offset+rows]]
		else:
			cats = Category.objects.filter(level=level, parent=parent)
			if term:
				cats = cats.filter(name__icontains=term)

			total = cats.count()
			data = [{'id': cat.id, 'text': cat.name}for cat in cats[offset:offset+rows]]
		
		return JsonResponse({'results': data, 'total': total})

@csrf_exempt
def overview(request):
	if request.method == 'GET':
		return render(request, 'psmd/overview.html')

	start = int(request.POST.get('start'))
	length = int(request.POST.get('length'))
	draw = int(request.POST.get('draw'))
	kingdom = int(request.POST.get('kingdom', 0))
	group = int(request.POST.get('group', 0))
	subgroup = int(request.POST.get('subgroup', 0))
	species = int(request.POST.get('species', 0))

	genomes = Genome.objects.all()

	if species:
		genomes = genomes.filter(pk=species)

	elif subgroup:
		genomes = genomes.filter(category=subgroup)

	elif group:
		genomes = genomes.filter(category__parent=group)

	elif kingdom:
		genomes = genomes.filter(category__parent__parent=kingdom)

	total = genomes.count()

	data = []
	for g in genomes[start:start+length]:
		data.append((g.taxonomy, g.species_name,  g.download_accession, g.size, g.gc_content, \
		g.ssr_count, g.ssr_frequency, g.ssr_density, g.cover, g.cm_count, g.cm_frequency, \
		g.cm_density, g.cssr_percent))

	return JsonResponse({
		'draw': draw,
		'recordsTotal': total,
		'recordsFiltered': total,
		'data': data
	})


@csrf_exempt
def species(request):
	#if request.method == 'POST':
	if request.method in ['GET', 'POST']:
		gid = int(request.POST.get('species', 716))
		
		genome = Genome.objects.get(pk=gid)
		data = {
			'kingdom': (genome.category.parent.parent.pk, genome.category.parent.parent.name),
			'group': (genome.category.parent.pk, genome.category.parent.name),
			'subgroup': (genome.category.pk, genome.category.name),
			'species': (genome.pk, genome.species_name),
			'common_name': genome.common_name,
			'taxonomy': genome.taxonomy,
			'accession': genome.download_accession,
			'assembly_level': genome.assembly_level,
			'gene_count': genome.gene_count
		}

		db_config = get_ssr_db(gid)
		with in_database(db_config):
			for stat in Summary.objects.all():
				make_plot(data, stat.content, stat.option)
		
		if int(data['cm_count']):
			data['cm_average'] = round(int(data['cssr_length'])/int(data['cm_count']), 2)
		else:
			data['cm_average'] = 0

		return render(request, 'psmd/species.html', {
			'summary': data
		})

@csrf_exempt
def browse(request):
	'''Browse perfect microsatellites
	'''
	gid = int(request.POST.get('species', 716))
	
	if 'draw' not in request.POST:
		genome = Genome.objects.get(pk=gid)
		species = {
			'kingdom': (genome.category.parent.parent.pk, genome.category.parent.parent.name),
			'group': (genome.category.parent.pk, genome.category.parent.name),
			'subgroup': (genome.category.pk, genome.category.name),
			'species': (genome.pk, genome.species_name)
		}
		return render(request, 'psmd/browse.html', {'species':species})

	
	if request.method == 'POST':
		db_config = get_ssr_db(gid)
		display = SSRDisplay(db_config, request.POST)
		return display.get_response()

@csrf_exempt
def compound(request):
	'''Browse compoud microsatellites
	'''
	if request.method == 'POST':
		gid = int(request.POST.get('species', 0))

		if 'draw' not in request.POST:
			genome = Genome.objects.get(pk=gid)
			species = {
				'kingdom': (genome.category.parent.parent.pk, genome.category.parent.parent.name),
				'group': (genome.category.parent.pk, genome.category.parent.name),
				'subgroup': (genome.category.pk, genome.category.name),
				'species': (genome.pk, genome.species_name)
			}
			return render(request, 'psmd/compound.html', {'species':species})

		db_config = get_ssr_db(gid)
		display = CSSRDisplay(db_config, request.POST)
		return display.get_response()

@csrf_exempt
def download(request):
	if request.method != 'POST':
		return

	mode = request.POST.get('mode')
	outfmt = request.POST.get('outfmt')
	gid = int(request.POST.get('species', 0))
	tid = request.POST.get('task', None)

	if gid:
		db_config = get_ssr_db(gid)
	elif tid:
		db_config = get_task_db(tid)

	if mode == 'ssr':
		filters = get_ssr_request_filters(request.POST)

		if filters:
			ssrs = SSR.objects.select_related().filter(**filters)
		else:
			ssrs = SSR.objects.select_related().all()

	elif mode == 'cssr':
		filters = get_cssr_request_filters(request.POST)

		if filters:
			ssrs = CSSR.objects.select_related().filter(**filters)
		else:
			ssrs = CSSR.objects.select_related().all()

	elif mode == 'issr':
		filters = get_issr_request_filters(request.POST)
		if filters:
			ssrs = ISSR.objects.select_related().filters(**filters)
		else:
			ssrs = ISSR.objects.select_related().all()

	return download_ssrs(db_config, ssrs, mode, tid, outfmt)

@csrf_exempt
def sequence(request):
	'''Get sequence accession or name
	'''
	if request.method == 'POST':
		term = request.POST.get('term', '')
		page = int(request.POST.get('page', 1))
		rows = int(request.POST.get('rows', 10))
		label = request.POST.get('label', 'name')
		gid = int(request.POST.get('species', 0))
		tid = request.POST.get('task', None)

		if gid:
			db_config = get_ssr_db(gid)
		elif tid:
			db_config = get_task_db(tid)

		with in_database(db_config):
			offset = (page-1)*rows
			
			seqs = Sequence.objects.all()
			
			if term:
				filters = {'{}__startswith'.format(label): term}
				seqs = Sequence.objects.filter(**filters)
				
			total = seqs.count()
			
			if label == 'accession':
				data = [{'id': seq.id, 'text': seq.accession} for seq in seqs[offset:offset+rows]]
			elif label == 'name':
				data = [{'id': seq.id, 'text': seq.name} for seq in seqs[offset:offset+rows]]

		return JsonResponse({'results': data, 'total': total})

@csrf_exempt
def flank(request):
	if request.method == 'POST':
		type_ = request.POST.get('type')
		gid = int(request.POST.get('species', 0))
		tid = request.POST.get('task', None)

		if gid:
			db_config = get_ssr_db(gid)
		
		elif tid:
			db_config = get_task_db(tid)

		if type_ == 'ssr':
			detail = SSRDetail(db_config, request.POST)

		elif type_ == 'cssr':
			detail = CSSRDetail(db_config, request.POST)

		elif type_ == 'issr':
			detail = ISSRDetail(db_config, request.POST)

		return detail.get_response()


@csrf_exempt
def krait(request):
	if request.method == 'GET':
		return render(request, 'psmd/krait.html')

	if request.method == 'POST':
		task_id = get_random_string(10)
		params = request.POST.dict()
		
		job_info = dict(
			job_id = task_id,
			mode = params['ssr_type'],
			fasta = params['input_message'],
			parameter = params['para_message']
		)
		
		if params['input_type'] == 'upload':
			try:
				params['input_file'] = upload_fasta_file(task_id, request.FILES['input_file'])
			except Exception as e:
				job_info['status'] = 3
				job_info['message'] = str(e)

		Job.objects.create(**job_info)

		#send task to celery
		if job_info.get('status', None) is None:
			search_ssrs.apply_async((params,), task_id=task_id)
		
		return JsonResponse({'task_id': task_id})

@csrf_exempt
def task(request, task_id):
	if request.method == 'GET':
		try:
			task = Job.objects.get(job_id=task_id)
		except Job.DoesNotExist:
			raise Http404('{} does not exist'.format(task_id))

		return render(request, 'psmd/task.html', {
			'task': task
		})

	elif request.method == 'POST':
		db_config = get_task_db(task_id)
		mode = request.POST.get('mode')

		if mode == 'ssr':
			display = SSRTaskDisplay(db_config, request.POST)
			return display.get_response()

		elif mode == 'cssr':
			display = CSSRTaskDisplay(db_config, request.POST)
			return display.get_response()

		elif mode == 'issr':
			display = ISSRTaskDisplay(db_config, request.POST)
			return display.get_response()

def analysis(request):
	return render(request, 'psmd/analysis.html')
