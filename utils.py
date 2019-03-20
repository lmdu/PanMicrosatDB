import os
import re
import csv
from dynamic_db_router import in_database
from django.http import StreamingHttpResponse, JsonResponse
from .config import Config
from .models import *

def colored_sequence(seq, start, end):
	pass

def color_base(b):
	return '<span class="B {0}">{0}</span>'.format(b)

def colored_seq(seq):
	'''
	colored the base from given dna sequence
	'''
	return ''.join(color_base(b) for b in seq)

def is_dna_base(b):
	return b in ['A', 'T', 'G', 'C', 'N']

def colored_cssr_pattern(pattern):
	return ''.join(color_base(b) if is_dna_base(b) else b for b in pattern)

def cssr_pattern_to_seq(pattern):
	'''
	convert compound ssr pattern to complete sequence
	e.g. (AACCCT)7AAACCCTA(AACCCT)5AACCCCTAAC(CCCTAA)6
	'''
	motifs = re.findall(r'\((\w+)\)(\d+)(\w*)', pattern)
	elements = []
	for motif, repeats, gap in motifs:
		elements.append(motif*int(repeats))
		if gap:
			elements.append(gap)

	return "".join(elements)

class Echo:
	def write(self, value):
		return value

def make_table(ssr):
	try:
		location = ssr.ssrannot.get_location_display()
	except:
		location = 'Intergenic'
	
	return (ssr.id, ssr.sequence.accession, ssr.sequence.name, ssr.start, ssr.end, ssr.motif, ssr.standard_motif, ssr.get_ssr_type_display(), ssr.repeats, ssr.length, location, ssr.ssrmeta.left_flank, ssr.ssrmeta.right_flank)

def make_gff(ssr):
	pass

def download_ssrs(db, ssrs, outfmt, outname):
	outfile = '{}.{}'.format(outname, outfmt)
	
	pseudo_writer = Echo()
	if outfmt == 'csv':
		writer = csv.writer(pseudo_writer)
	else:
		writer = csv.writer(pseudo_writer, delimiter='\t')

	targets = [make_table(ssr) for ssr in ssrs]

	#def ssrs_iter():
	#	yield writer.writerow(['ID', 'Seqacc', 'Seqname', 'Start', 'End', 'Motif', 'Standmotif', 'Type', 'Repeats', 'Length', 'Location', 'Leftflank', 'Rightflank'])

	#	with in_database(db):
	#		for ssr in ssrs:
	#			yield writer.writerow(make_table(ssr))

	
	response = StreamingHttpResponse(
		streaming_content = targets,
		content_type='text/csv'
	)
	response['Content-Disposition'] = 'attachment; filename="{}"'.format(outfile)
	
	return response

def get_ssr_db(gid):
	'''Get ssr db file for specified species
	@para gid, species genome id in genome table
	@return dict, used for dynamic router connection
	'''
	try:
		genome = Genome.objects.get(pk=gid)
	except Genome.DoesNotExist:
		return None
	
	sub_dir = os.path.join(genome.category.parent.parent.name, genome.category.parent.name, genome.category.name)
	sub_dir = sub_dir.replace(' ', '_').replace(',', '')
	db_file = os.path.join(Config.DB_DIR, sub_dir, '{}.db'.format(genome.download_accession))

	db_config = {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': db_file
	}

	return db_config

def get_task_db(tid):
	db_file = os.path.join(Config.TASK_RESULT_DIR, '{}.db'.format(tid))
	db_config = {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': db_file
	}

	return db_config

def get_ssrs(params, db):
	draw = int(params.get('draw'))

	#action (download or view)
	action = params.get('action', 'view')

	#download parameters
	if action == 'download':
		outname = params.get('outname')
		outfmt = params.get('outfmt')

	#datatable parameters
	if action == 'view':
		start = int(params.get('start'))
		length = int(params.get('length'))

	#filter parameters
	seqid = int(params.get('sequence', 0))
	begin = int(params.get('begin', 0))
	end = int(params.get('end', 0))
	motif = params.get('motif')
	smotif = params.get('smotif')
	ssrtype = int(params.get('ssrtype', 0))
	repsign = params.get('repsign')
	repeats = int(params.get('repeats', 0))
	max_repeats = int(params.get('maxrep', 0))
	lensign = params.get('lensign')
	ssrlen = int(params.get('ssrlen', 0))
	max_ssrlen = int(params.get('maxlen', 0))

	with in_database(db):
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

		##download ssrs as file
		if action == 'download':
			return download_ssrs(db_config, ssrs, outfmt, outname)

		##view ssrs for datatable
		filtered_total = ssrs.count()

		#order by
		colidx = params.get('order[0][column]')
		colname = params.get('columns[{}][name]'.format(colidx))
		sortdir = params.get('order[0][dir]')

		if sortdir == 'asc':
			ssrs = ssrs.order_by(colname)
		else:
			ssrs = ssrs.order_by('-{}'.format(colname))

		data = []
		for ssr in ssrs[start:start+length]:
			data.append((ssr.id, ssr.sequence.name, ssr.start, ssr.end, colored_seq(ssr.motif), \
				colored_seq(ssr.standard_motif), ssr.get_ssr_type_display(), ssr.repeats, ssr.length))

	return JsonResponse({
		'draw': draw,
		'recordsTotal': total,
		'recordsFiltered': filtered_total,
		'data': data
	})
