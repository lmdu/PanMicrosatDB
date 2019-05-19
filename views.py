import re
import json
import math
import datetime

from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.db import connections
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string

from .models import *
from .utils import *
from .plots import *
from .tasks import *
from .display import *
from .downloader import *
from .router import in_database
from .thirds.motifs import motif_to_number

# Create your views here.
def index(request):
	try:
		v = News.objects.filter(category=1).latest('created')
	except News.DoesNotExist:
		version = '0.1'
		release = datetime.datetime.now()
	else:
		version = v.title.split()[1]
		release = v.created

	posts = News.objects.order_by('-id')[:10]

	return render(request, 'psmd/index.html', {
		'version': version,
		'release': release,
		'posts': posts
	})

@csrf_exempt
def search(request):
	if request.method == 'POST':
		term = request.POST.get('term')
		genomes = Genome.objects.filter(Q(taxonomy__icontains=term) | Q(species_name__icontains=term) \
			| Q(common_name__icontains=term) | Q(download_accession__icontains=term))[:10]

		def format_val(*items):
			res = ['<tr data-id="{}">'.format(items[0])]
			for item in items[1:]:
				res.append('<td>{}</td>'.format(re.sub(r'(?i)({})'.format(term), r'<b>\1</b>', item)))
			res.append('</tr>')
			return ''.join(res)

		res = [format_val(g.id, g.taxonomy, g.species_name, g.common_name, g.download_accession) for g in genomes]


		return JsonResponse({'data': ''.join(res)})

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
	unit = request.POST.get('unit', 'GB')

	fields = ['id', 'taxonomy', 'species_name', 'download_accession', 'size', 'gc_content',
			  'ssr_count', 'ssr_frequency', 'ssr_density', 'cover', 'cm_count', 'cm_frequency',
			  'cm_density', 'cssr_percent']

	genomes = Genome.objects.all()
	total = genomes.count()
	filters = Filters()
	filters.add('id', species)
	filters.add('category', subgroup)
	filters.add('category__parent', group)
	filters.add('category__parent__parent', kingdom)

	#filter
	if filters:
		genomes = Genome.objects.filter(**filters)
		filtered_count = genomes.count()
	else:
		filtered_count = total

	#sort order
	colidx = int(request.POST.get('order[0][column]'))
	sortdir = request.POST.get('order[0][dir]')

	if fields[colidx] == 'taxonomy':
		if sortdir == 'asc':
			genomes = genomes.extra({'taxon': "CAST(taxonomy as UNSIGNED)"}).order_by('taxon')
		else:
			genomes = genomes.extra({'taxon': "CAST(taxonomy as UNSIGNED)"}).order_by('-taxon')
	else:
		if sortdir == 'asc':
			genomes = genomes.order_by(fields[colidx])
		else:
			genomes = genomes.order_by('-{}'.format(fields[colidx]))

	data = []
	for g in genomes[start:start+length]:
		data.append((g.id, g.taxonomy, g.species_name,  g.download_accession,
			humanized_genome_size(g.size, unit), 
			humanized_round(g.gc_content),
			g.ssr_count,
			humanized_round(g.ssr_frequency),
			humanized_round(g.ssr_density),
			humanized_round(g.cover),
			g.cm_count,
			humanized_round(g.cm_frequency),
			humanized_round(g.cm_density),
			humanized_round(g.cssr_percent)
		))

	return JsonResponse({
		'draw': draw,
		'recordsTotal': total,
		'recordsFiltered': filtered_count,
		'data': data
	})


@csrf_exempt
def species(request):
	if request.method == 'POST':
	#if request.method in ['GET', 'POST']:
		gid = int(request.POST.get('species', 0))
		
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
		location_show = display_location(gid)
		species = {
			'kingdom': (genome.category.parent.parent.pk, genome.category.parent.parent.name),
			'group': (genome.category.parent.pk, genome.category.parent.name),
			'subgroup': (genome.category.pk, genome.category.name),
			'species': (genome.pk, genome.species_name)
		}
		return render(request, 'psmd/browse.html', {'species':species, 'location_show': location_show})

	
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
			location_show = display_location(gid)
			species = {
				'kingdom': (genome.category.parent.parent.pk, genome.category.parent.parent.name),
				'group': (genome.category.parent.pk, genome.category.parent.name),
				'subgroup': (genome.category.pk, genome.category.name),
				'species': (genome.pk, genome.species_name)
			}
			return render(request, 'psmd/compound.html', {'species':species, 'location_show': location_show})

		db_config = get_ssr_db(gid)
		display = CSSRDisplay(db_config, request.POST)
		return display.get_response()

@csrf_exempt
def download(request):
	if request.method != 'POST':
		return

	mode = request.POST.get('mode')
	
	#download statistics
	if 'statistics' in mode:
		return download_statistics(request.POST)
	
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

@csrf_exempt
def analysis(request):
	if request.method == 'GET':
		return render(request, 'psmd/analysis.html')

	if request.method == 'POST':
		species = request.POST.getlist('species[]', [])
		species_names = [g.species_name for g in Genome.objects.filter(id__in=species)]
		species_datas = []
		for sid in species:
			db_config = get_ssr_db(sid)
			with in_database(db_config):
				species_datas.append({stat.option:stat.content for stat in Summary.objects.all()})

		charts = {'species_categories': species_names}
		#ssr frequency and density plot
		charts['ssr_freq_dens_line'] = {
			'frequency': [float(sp['ssr_frequency']) for sp in species_datas],
			'density': [float(sp['ssr_density']) for sp in species_datas]
		}

		charts['cssr_freq_dens_line'] = {
			'frequency': [float(sp['cssr_frequency']) for sp in species_datas],
			'density': [float(sp['cssr_density']) for sp in species_datas]
		}

		charts['ssr_cover_cssrp_line'] = {
			'cover': [float(sp['genome_cover']) for sp in species_datas],
			'cssrp': [float(sp['cssr_percent']) for sp in species_datas]
		}

		#ssr motif heatmap plot
		items = ["species,motif,counts"]
		motif_datas = [json.loads(sp['ssr_motif']) for sp in species_datas]
		motif_types = sorted({m for d in motif_datas for m in d}, key=motif_to_number)

		for i, counts in enumerate(motif_datas):
			for j, motif in enumerate(motif_types):
				v = int(counts.get(motif, 0))
				if v > 0:
					v = math.log(v, 10)
				items.append("{},{},{}".format(i, j, v))

		charts['ssr_motif_heatmap'] = {
			'motifs': motif_types,
			'counts': "\n".join(items)
		}

		#ssr repats distribution plot
		
		items = ["species,repeat,counts"]
		repeat_data = []
		for sp in species_datas:
			d = json.loads(sp['ssr_repdis'])
			rep_data = {}
			for _, rc in d.items():
				for r, c in rc.items():
					rep_data[int(r)] = rep_data.get(int(r), 0) + int(c)
			repeat_data.append(rep_data)
		repeats = sorted({r for d in repeat_data for r in d})

		for i, counts in enumerate(repeat_data):
			for j, repeat in enumerate(repeats):
				v = counts.get(repeat, 0)
				if v > 0:
					v = math.log(v, 10)

				items.append("{},{},{}".format(i, j, v))

		charts['ssr_repeat_heatmap'] = {
			'repeats': repeats,
			'counts': "\n".join(items)
		}		

		#ssr type distribution plot
		types = ['Mono', 'Di', 'Tri', 'Tetra', 'Penta', 'Hexa']
		items = [{'name':t, 'data': []} for t in types]
		for sp in species_datas:
			d = json.loads(sp['ssr_types'])
			for t, c in d.items():
				items[types.index(t)]['data'].append(c)

		charts['ssr_type_stack_bar'] = items
		

		return JsonResponse(charts)


def help(request):
	return render(request, 'psmd/help.html')
