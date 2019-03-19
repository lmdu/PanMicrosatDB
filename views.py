from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections
from dynamic_db_router import in_database
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string

from .models import *
from .utils import *
from .plots import *
from .tasks import *

import re
import json
import primer3

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
		draw = int(request.POST.get('draw'))

		db_config = get_ssr_db(gid)

		#action (download or view)
		action = request.POST.get('action', 'view')

		#download parameters
		if action == 'download':
			outname = request.POST.get('outname')
			outfmt = request.POST.get('outfmt')

		#datatable parameters
		if action == 'view':
			start = int(request.POST.get('start'))
			length = int(request.POST.get('length'))

		#filter parameters
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

		with in_database(db_config):
			#total = int(SSRStat.objects.get(name='ssr_count').val)
			ssrs = SSR.objects.all()
			total = ssrs.count()

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

			##download ssrs as file
			if action == 'download':
				return download_ssrs(db_config, ssrs, outfmt, outname)

			##view ssrs for datatable
			filtered_total = ssrs.count()

			#order by
			colidx = request.POST.get('order[0][column]')
			colname = request.POST.get('columns[{}][name]'.format(colidx))
			sortdir = request.POST.get('order[0][dir]')

			if sortdir == 'asc':
				ssrs = ssrs.order_by(colname)
			else:
				ssrs = ssrs.order_by('-{}'.format(colname))

			data = []
			for ssr in ssrs[start:start+length]:
				try:
					location = ssr.ssrannot.get_location_display()
				except:
					location = 'Intergenic'
				
				data.append((ssr.id, ssr.sequence.accession, ssr.sequence.name, \
				 ssr.start, ssr.end, colored_seq(ssr.motif), colored_seq(ssr.standard_motif), \
				 ssr.get_ssr_type_display(), ssr.repeats, ssr.length, location))

		return JsonResponse({
			'draw': draw,
			'recordsTotal': total,
			'recordsFiltered': filtered_total,
			'data': data
		})

@csrf_exempt
def cssrs_browse(request):
	#if request.method == 'GET':
	#	return render(request, 'psmd/cssrs.html')
	
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
			return render(request, 'psmd/cssrs.html', {'species':species})

		db_config = get_ssr_db(gid)

		start = int(request.POST.get('start'))
		length = int(request.POST.get('length'))
		draw = int(request.POST.get('draw'))

		#filter parameters
		seqid = int(request.POST.get('sequence', 0))
		begin = int(request.POST.get('begin', 0))
		end = int(request.POST.get('end', 0))
		cpxsign = request.POST.get('cpxsign')
		complexity = int(request.POST.get('complex', 0))
		max_complexity = int(request.POST.get('maxcpx', 0))
		lensign = request.POST.get('lensign')
		ssrlen = int(request.POST.get('ssrlen', 0))
		max_ssrlen = int(request.POST.get('maxlen', 0))
		location = int(request.POST.get('location', 0))

		data = []
		with in_database(db_config):
			cssrs = CSSR.objects.all()
			total = cssrs.count()

			if seqid:
				cssrs = cssrs.filter(sequence=seqid)

			if begin and end:
				cssrs = cssrs.filter(start__gte=begin, end__lte=end)

			if complexity:
				if cpxsign == 'gt':
					cssrs = cssrs.filter(complexity__gt=complexity)
				elif cpxsign == 'gte':
					cssrs = cssrs.filter(complexity__gte=complexity)
				elif cpxsign == 'eq':
					cssrs = cssrs.filter(complexity=complexity)
				elif cpxsign == 'lt':
					cssrs = cssrs.filter(complexity__lt=complexity)
				elif cpxsign == 'lte':
					cssrs = cssrs.filter(complexity__lte=complexity)
				elif cpxsign == 'in':
					cssrs = cssrs.filter(complexity__range=(complexity, max_complexity))

			if ssrlen:
				if lensign == 'gt':
					cssrs = cssrs.filter(length__gt=ssrlen)
				elif lensign == 'gte':
					cssrs = cssrs.filter(length__gte=ssrlen)
				elif lensign == 'eq':
					cssrs = cssrs.filter(length=ssrlen)
				elif lensign == 'lt':
					cssrs = cssrs.filter(length__lt=ssrlen)
				elif lensign == 'lte':
					cssrs = cssrs.filter(length__lte=ssrlen)
				elif lensign == 'in':
					cssrs = cssrs.filter(length__range=(ssrlen, max_ssrlen))

			if location:
				cssrs = cssrs.filter(cssrannot__location=location)

			#order by
			colidx = request.POST.get('order[0][column]')
			colname = request.POST.get('columns[{}][name]'.format(colidx))
			sortdir = request.POST.get('order[0][dir]')

			if sortdir == 'asc':
				cssrs = cssrs.order_by(colname)
			else:
				cssrs = cssrs.order_by('-{}'.format(colname))

			for cssr in cssrs[start:start+length]:
				try:
					location = cssr.cssrannot.get_location_display()
				except:
					location = 'Intergenic'

				pattern = colored_cssr_pattern(cssr.structure)
				pattern = re.sub(r'(\d+)', lambda m: '<sub>'+m.group(0)+'</sub>', pattern)

				data.append((cssr.id, cssr.sequence.accession, cssr.sequence.name, cssr.start, \
				 cssr.end, cssr.complexity, cssr.length, pattern, location))

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
		gid = int(request.POST.get('species'))

		db_config = get_ssr_db(gid)

		with in_database(db_config) as db:
			offset = (page-1)*rows
			if term:
				if label == 'accession':
					total = Sequence.objects.filter(accession__startswith=term).count()
					seqs = Sequence.objects.filter(accession__startswith=term)[offset:offset+rows]
					data = [{'id': seq.rowid, 'text': seq.accession} for seq in seqs]

				elif label == 'name':
					total = Sequence.objects.filter(name__startswith=term).count()
					seqs = Sequence.objects.filter(name__startswith=term)[offset:offset+rows]
					data = [{'id': seq.id, 'text': seq.name} for seq in seqs]
				
				#term = '{}*'.format(term)
				#with connections[db.unique_db_id].cursor() as cursor:
				#	cursor.execute("SELECT COUNT(*) FROM search WHERE search MATCH %s", (term,))
				#	total = cursor.fetchone()[0]
				
				#seqs = Search.objects.raw("SELECT rowid,name,accession FROM search WHERE search MATCH %s LIMIT %s,%s", (term, offset, rows))

				#if label == 'accession':
				#	data = [{'id': seq.rowid, 'text': seq.accession} for seq in seqs]
				#elif label == 'name':
				#	data = [{'id': seq.rowid, 'text': seq.name} for seq in seqs]
			else:
				total = int(Summary.objects.get(option='seq_count').content)
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
		gid = int(request.POST.get('species'))
		type_ = request.POST.get('type')
		
		db_config = get_ssr_db(gid)

		with in_database(db_config):
			if type_ == 'ssr':
				ssr = SSR.objects.get(pk=ssr_id)
				ssrmeta = ssr.ssrmeta
				try:
					ssrannot = ssr.ssrannot
					gene = ssrannot.gene
				except:
					ssrannot = None
					gene = None
			
			elif type_ == 'cssr':
				ssr = CSSR.objects.get(pk=ssr_id)
				ssrmeta = ssr.cssrmeta
				try:
					ssrannot = ssr.cssrannot
					gene = ssrannot.gene
				except:
					ssrannot = None
					gene = None

			else:
				return None

		nucleotide = """
		<div class="sequence-nucleotide">
			<div class="base-row sequence-box">
				<span class="nucleobase {0}">{0}</span>
			</div>
			<div class="meta-row sequence-box">
				<span class="meta-info"></span>
			</div>
		</div>
		"""

		target = """
		<div class="sequence-nucleotide">
			<div class="base-row sequence-box">
				<span class="nucleobase-target {0}">{0}</span>
			</div>
			<div class="meta-row sequence-box">
				<span class="meta-info">{1}</span>
			</div>
		</div>
		"""

		html = []

		for b in ssrmeta.left_flank:
			html.append(nucleotide.format(b))

		if type_ == 'ssr':
			ssr_seq = "".join([ssr.motif]*ssr.repeats)
		elif type_ == 'cssr':
			ssr_seq = cssr_pattern_to_seq(ssr.structure)

		for i,b in enumerate(ssr_seq):
			if i == 0:
				html.append(target.format(b, ssr.start))
			elif i + 1 == len(ssr_seq):
				html.append(target.format(b, ssr.end))
			else:
				html.append(target.format(b, ''))

		for b in ssrmeta.right_flank:
			html.append(nucleotide.format(b))

		#get ssr location
		if ssrannot:
			loc = ssrannot.get_location_display()
			gid = gene.gid
			name = gene.name
			biotype = gene.biotype
			dbxref = gene.dbxref
			lochtml = "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(gid, name, biotype, dbxref, loc)
		else:
			lochtml = '<tr><td class="text-center" colspan="4">N/A</td><td>Intergenic</td></tr>'

		res = primer3.bindings.designPrimers({
			'SEQUENCE_ID': ssr.id,
			'SEQUENCE_TEMPLATE': "{}{}{}".format(ssrmeta.left_flank, ssr_seq, ssrmeta.right_flank),
			'SEQUENCE_TARGET': [len(ssrmeta.left_flank), len(ssr_seq)],
			'SEQUENCE_INTERNAL_EXCLUDED_REGION': [len(ssrmeta.left_flank), len(ssr_seq)]
		},
		{
			'PRIMER_TASK': 'generic',
			'PRIMER_PICK_LEFT_PRIMER': 1,
			'PRIMER_PICK_INTERNAL_OLIGO': 0,
			'PRIMER_PICK_RIGHT_PRIMER': 1,
			'PRIMER_PRODUCT_SIZE_RANGE': [[100,300]],
			'PRIMER_NUM_RETURN': 3,
			'PRIMER_MIN_SIZE': 18,
			'PRIMER_OPT_SIZE': 20,
			'PRIMER_MAX_SIZE': 27,
			'PRIMER_MIN_GC': 30,
			'PRIMER_MAX_GC': 80,
			'PRIMER_GC_CLAMP': 2,
			'PRIMER_MIN_TM': 58,
			'PRIMER_OPT_TM': 60,
			'PRIMER_MAX_TM': 65,
			'PRIMER_MAX_SELF_ANY_TH': 47,
			'PRIMER_MAX_SELF_END_TH': 47,
			'PRIMER_PAIR_MAX_COMPL_ANY_TH': 47,
			'PRIMER_PAIR_MAX_COMPL_END_TH': 47,
			'PRIMER_MAX_HAIRPIN_TH': 47,
			'PRIMER_MAX_END_STABILITY': 99,
			'PRIMER_MAX_NS_ACCEPTED': 5,
			'PRIMER_MAX_POLY_X': 0,
			'PRIMER_PAIR_MAX_DIFF_TM': 2
		})

		primer_count = res['PRIMER_PAIR_NUM_RETURNED']
		primers = []
		if primer_count:
			for i in range(primer_count):
				num = i + 1
				product = res['PRIMER_PAIR_{}_PRODUCT_SIZE'.format(i)]
				forward = colored_seq(res['PRIMER_LEFT_{}_SEQUENCE'.format(i)])
				tm1 = round(res['PRIMER_LEFT_{}_TM'.format(i)], 2)
				gc1 = round(res['PRIMER_LEFT_{}_GC_PERCENT'.format(i)], 2)
				stab1 = round(res['PRIMER_LEFT_{}_END_STABILITY'.format(i)], 2)
				reverse = colored_seq(res['PRIMER_RIGHT_{}_SEQUENCE'.format(i)])
				tm2 = round(res['PRIMER_RIGHT_{}_TM'.format(i)], 2)
				gc2 = round(res['PRIMER_RIGHT_{}_GC_PERCENT'.format(i)], 2)
				stab2 = round(res['PRIMER_RIGHT_{}_END_STABILITY'.format(i)], 2)

				html_str = """
				<tr><td class="align-middle" rowspan="2">{}</td><td>Forward</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td class="align-middle" rowspan="2">{}</td></tr>
				<tr><td>Reverse</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>
				"""
				primers.append(html_str.format(num, forward, tm1, gc1, stab1, product, reverse, tm2, gc2, stab2))

			primers = "".join(primers)
		else:
			primers = '<tr><td class="text-center" colspan="7">N/A</td></tr>'

		return JsonResponse(dict(
			seq = "".join(html), 
			location = lochtml,
			primer = primers
		))

@csrf_exempt
def get_cssr_detail(request):
	if request.method == 'POST':
		ssr_id = int(request.POST.get('ssrid'))
		gid = int(request.POST.get('species'))
		
		db_config = get_ssr_db(gid)

		with in_database(db_config):
			cssr = CSSR.objects.get(pk=ssr_id)
			cssrmeta = cssr.cssrmeta
			try:
				cssrannot = cssr.cssrannot
				gene = cssrannot.gene
			except:
				cssrannot = None
				gene = None

		nucleotide = """
		<div class="sequence-nucleotide">
			<div class="base-row sequence-box">
				<span class="nucleobase {0}">{0}</span>
			</div>
			<div class="meta-row sequence-box">
				<span class="meta-info"></span>
			</div>
		</div>
		"""

		target = """
		<div class="sequence-nucleotide">
			<div class="base-row sequence-box">
				<span class="nucleobase-target {0}">{0}</span>
			</div>
			<div class="meta-row sequence-box">
				<span class="meta-info">{1}</span>
			</div>
		</div>
		"""

		html = []

		for b in cssrmeta.left_flank:
			html.append(nucleotide.format(b))

		cssr_seq = cssr_pattern_to_seq(cssr.structure)

		for i,b in enumerate(cssr_seq):
			if i == 0:
				html.append(target.format(b, cssr.start))
			elif i + 1 == len(cssr_seq):
				html.append(target.format(b, cssr.end))
			else:
				html.append(target.format(b, ''))

		for b in cssrmeta.right_flank:
			html.append(nucleotide.format(b))

		#get ssr location
		if cssrannot:
			loc = cssrannot.get_location_display()
			gid = gene.gid
			name = gene.name
			biotype = gene.biotype
			dbxref = gene.dbxref
			lochtml = "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(gid, name, biotype, dbxref, loc)
		else:
			lochtml = '<tr><td class="text-center" colspan="4">N/A</td><td>Intergenic</td></tr>'

		res = primer3.bindings.designPrimers({
			'SEQUENCE_ID': cssr.id,
			'SEQUENCE_TEMPLATE': "{}{}{}".format(cssrmeta.left_flank, cssr_seq, cssrmeta.right_flank),
			'SEQUENCE_TARGET': [len(cssrmeta.left_flank), len(cssr_seq)],
			'SEQUENCE_INTERNAL_EXCLUDED_REGION': [len(cssrmeta.left_flank), len(cssr_seq)]
		},
		{
			'PRIMER_TASK': 'generic',
			'PRIMER_PICK_LEFT_PRIMER': 1,
			'PRIMER_PICK_INTERNAL_OLIGO': 0,
			'PRIMER_PICK_RIGHT_PRIMER': 1,
			'PRIMER_PRODUCT_SIZE_RANGE': [[100,300]],
			'PRIMER_NUM_RETURN': 3,
			'PRIMER_MIN_SIZE': 18,
			'PRIMER_OPT_SIZE': 20,
			'PRIMER_MAX_SIZE': 27,
			'PRIMER_MIN_GC': 30,
			'PRIMER_MAX_GC': 80,
			'PRIMER_GC_CLAMP': 2,
			'PRIMER_MIN_TM': 58,
			'PRIMER_OPT_TM': 60,
			'PRIMER_MAX_TM': 65,
			'PRIMER_MAX_SELF_ANY_TH': 47,
			'PRIMER_MAX_SELF_END_TH': 47,
			'PRIMER_PAIR_MAX_COMPL_ANY_TH': 47,
			'PRIMER_PAIR_MAX_COMPL_END_TH': 47,
			'PRIMER_MAX_HAIRPIN_TH': 47,
			'PRIMER_MAX_END_STABILITY': 99,
			'PRIMER_MAX_NS_ACCEPTED': 5,
			'PRIMER_MAX_POLY_X': 0,
			'PRIMER_PAIR_MAX_DIFF_TM': 2
		})

		primer_count = res['PRIMER_PAIR_NUM_RETURNED']
		primers = []
		if primer_count:
			for i in range(primer_count):
				num = i + 1
				product = res['PRIMER_PAIR_{}_PRODUCT_SIZE'.format(i)]
				forward = colored_seq(res['PRIMER_LEFT_{}_SEQUENCE'.format(i)])
				tm1 = round(res['PRIMER_LEFT_{}_TM'.format(i)], 2)
				gc1 = round(res['PRIMER_LEFT_{}_GC_PERCENT'.format(i)], 2)
				stab1 = round(res['PRIMER_LEFT_{}_END_STABILITY'.format(i)], 2)
				reverse = colored_seq(res['PRIMER_RIGHT_{}_SEQUENCE'.format(i)])
				tm2 = round(res['PRIMER_RIGHT_{}_TM'.format(i)], 2)
				gc2 = round(res['PRIMER_RIGHT_{}_GC_PERCENT'.format(i)], 2)
				stab2 = round(res['PRIMER_RIGHT_{}_END_STABILITY'.format(i)], 2)

				html_str = """
				<tr><td class="align-middle" rowspan="2">{}</td><td>Forward</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td class="align-middle" rowspan="2">{}</td></tr>
				<tr><td>Reverse</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>
				"""
				primers.append(html_str.format(num, forward, tm1, gc1, stab1, product, reverse, tm2, gc2, stab2))

			primers = "".join(primers)
		else:
			primers = '<tr><td colspan="7">N/A</td></tr>'

		return JsonResponse(dict(
			seq = "".join(html), 
			location = lochtml,
			primer = primers
		))

@csrf_exempt
def krait(request):
	if request.method == 'GET':
		return render(request, 'psmd/krait.html')

	if request.method == 'POST':
		task_id = get_random_string(10)
		params = request.POST

		search_ssrs.apply_async((params,), task_id=task_id)

		return JsonResponse(dict(
			task_id = task_id
		))

def task(request, task_id):
	task = search_ssrs.AsyncResult(task_id)

	return render(request, 'psmd/task.html', {
		'state': task.state
	})
		

