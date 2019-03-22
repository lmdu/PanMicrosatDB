import os
import re

from .config import Config
from .models import *

class AttributedDict(dict):
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(key)

	def __setattr__(self, key, val):
		self[key] = val

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

def upload_fasta_file(tid, infile):
	if infile.size > 104857600:
		raise Exception('Upload file {} size > 100M'.format(infile.name))

	if infile.name.endswith('.gz'):
		destname = '{}.fa.gz'.format(tid)
	else:
		destname = '{}.fa'.format(tid)

	fa_file = os.path.join(Config.TASK_FASTA_DIR, destname)

	with open(fa_file, 'wb+') as fw:
		for chunk in infile.chunks():
			fw.write(chunk)

	return fa_file

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

class Filters(dict):
	def add(self, field, val, sign=None):
		if isinstance(val, tuple):
			if not val[0] or not val[1]:
				return

			if not val[1]:
				val = val[0]

		else:
			if not val:
				return

		if sign is None or sign == 'eq':
			k = field
		else:
			k = '{}__{}'.format(field, sign)
		
		self[k] = val

def get_ssr_request_filters(params):
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
	location = int(params.get('location', 0))

	filters = Filters()
	filters.add('sequence', seqid)
	filters.add('start', begin, 'gte')
	filters.add('end', end, 'lte')
	filters.add('motif', motif)
	filters.add('standard_motif', smotif)
	filters.add('ssr_type', ssrtype)
	filters.add('repeats', (repeats, max_repeats), repsign)
	filters.add('length', (ssrlen, max_ssrlen), lensign)
	filters.add('ssrannot__location', location)

	return filters

def get_cssr_request_filters(params):
	#filter parameters
	seqid = int(params.get('sequence', 0))
	begin = int(params.get('begin', 0))
	end = int(params.get('end', 0))
	cpxsign = params.get('cpxsign')
	complexity = int(params.get('complex', 0))
	max_complexity = int(params.get('maxcpx', 0))
	lensign = params.get('lensign')
	ssrlen = int(params.get('ssrlen', 0))
	max_ssrlen = int(params.get('maxlen', 0))
	location = int(params.get('location', 0))

	filters = Filters()
	filters.add('sequence', seqid)
	filters.add('start', begin, 'gte')
	filters.add('end', end, 'lte')
	filters.add('complexity', (complexity, max_complexity), cpxsign)
	filters.add('length', (ssrlen, max_ssrlen), lensign)
	filters.add('cssrannot__location', location)

	return filters

def get_datatable_params(post):
	params = AttributedDict()
	#datatable paramers
	params.draw = int(post.get('draw'))
	params.start = int(post.get('start'))
	params.length = int(post.get('length'))
	#order by
	params.colidx = post.get('order[0][column]')
	params.colname = post.get('columns[{}][name]'.format(params.colidx))
	params.sortdir = post.get('order[0][dir]')

	return params

def get_primer_setttings(post):
	settings = AttributedDict()

	settings.PRIMER_TASK = 'generic'
	settings.PRIMER_PICK_LEFT_PRIMER = 1
	settings.PRIMER_PICK_INTERNAL_OLIGO = 0
	settings.PRIMER_PICK_RIGHT_PRIMER = 1
	for k in post:
		if k.startswith('PRIMER_'):
			if k == 'PRIMER_PRODUCT_SIZE_RANGE':
				pass
			else:
				settings[k] = float(post.get(k))

	'''
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
	'''
 