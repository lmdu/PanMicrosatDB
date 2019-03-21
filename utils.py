import os
import re
import csv
import time
import sqlite3
from django.http import StreamingHttpResponse, JsonResponse
from django.db import connection

from .router import in_database
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

def get_output_ssr(ssr):
	locations = {1: 'CDS', 2: 'exon', 3: '3UTR', 4: 'intron', 5: '5UTR'}
	locaton = locations.get(ssr[16], 'Intergenic')
	return (ssr[0], ssr[10], ssr[11], ssr[2], ssr[3], ssr[4], ssr[5], ssr[6], ssr[7], ssr[8], \
		locaton, ssr[13], ssr[14])

class BaseDownloader(object):
	def __init__(self, db, ssrs, outfmt):
		self.headers = None
		self.base_sql = None
		self.query = str(ssrs.query)
		self.outfmt = outfmt
		self.conn = sqlite3.connect(db['NAME'])

		if self.outfmt == 'gff':
			self.format = self.gff_format
		else:
			self.format = self.tab_format

		pseudo_writer = Echo()
		if outfmt == 'csv':
			self.writer = csv.writer(pseudo_writer)
		else:
			self.writer = csv.writer(pseudo_writer, delimiter='\t')

		self.locations = {1: 'CDS', 2: 'exon', 3: '3UTR', 4: 'intron', 5: '5UTR'}

	def get_location(self, locid):
		return self.locations.get(locid, 'N/A')

	@property
	def sql(self):
		try:
			where = self.query.split('WHERE')[1].replace('"', '')
		except IndexError:
			where = None

		if where is not None:
			query = "{} WHERE {}".format(self.base_sql, where)
		else:
			query = self.base_sql

		return query

	def tab_format(self, r):
		pass

	def gff_format(self, r):
		pass

	def iter(self):
		if self.headers:
			yield self.writer.writerow(self.headers)

		cursor = self.conn.cursor()
		for row in cursor.execute(self.sql):
			yield self.writer.writerow(self.format(row))

		self.conn.close()

class SSRDownloader(BaseDownloader):
	def __init__(self, db, ssrs, outfmt):
		super(SSRDownloader, self).__init__(db, ssrs, outfmt)
		self.base_sql = ("SELECT * FROM ssr INNER JOIN sequence AS s ON (s.id=ssr.sequence_id)"
				" INNER JOIN ssrmeta AS m ON (m.ssr_id=ssr.id)"
				" LEFT JOIN ssrannot AS a ON (a.ssr_id=ssr.id)")

		if outfmt != 'gff':
			self.headers = ['#ID', 'Seqacc', 'Seqname', 'Start', 'End', 'Motif', 'Standmotif', \
							'Type', 'Repeats', 'Length', 'Location', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		locaton = self.get_location(row[16])
		return (row[0], row[10], row[11], row[2], row[3], row[4], row[5], row[6], row[7], \
		 		row[8], locaton, row[13], row[14])

	def gff_format(self, row):
		pass


def download_ssrs(db, ssrs, ssrtype, outfmt):
	outfile = '{}-{}.{}'.format(ssrtype.upper(), time.strftime("%Y%m%d-%H%M%S"), outfmt)

	if ssrtype == 'ssr':
		loader = SSRDownloader(db, ssrs, outfmt)

	response = StreamingHttpResponse(
		streaming_content = loader.iter(),
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

class Filters(dict):
	def add(self, field, val, sign=None):
		if isinstance(val, tuple):
			if not val[0] or not val[1]:
				return
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
 