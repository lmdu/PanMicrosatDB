import os
import csv
import time
import json
import sqlite3

from django.http import StreamingHttpResponse
from .models import Genome, Summary
from .config import Config
from .router import in_database
from .utils import humanized_genome_size, Filters

class Echo:
	def write(self, value):
		return value

class BaseDownloader(object):
	def __init__(self, db, ssrs, outfmt):
		self.query = str(ssrs.query)
		self.outfmt = outfmt
		self.conn = sqlite3.connect(db['NAME'])

		if self.outfmt == 'gff':
			self.format = self.gff_format
		else:
			self.format = self.tab_format

		pseudo_writer = Echo()
		if self.outfmt == 'csv':
			self.writer = csv.writer(pseudo_writer)
		else:
			self.writer = csv.writer(pseudo_writer, delimiter='\t')

		self.locations = {1: 'CDS', 2: 'exon', 3: '3UTR', 4: 'intron', 5: '5UTR'}
		self.ssrtypes = {1: 'Mono', 2: 'Di', 3: 'Tri', 4: 'Tetra', 5: 'Penta', 6: 'Hexa'}

	@property
	def base_sql(self):
		pass

	@property
	def headers(self):
		pass

	def get_location(self, lid):
		return self.locations.get(lid, 'N/A')

	def get_ssr_type(self, tid):
		self.ssrtypes.get(tid)

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

	def tab_format(self, row):
		pass

	def gff_format(self, row):
		pass

	def iter(self):
		if self.outfmt != 'gff':
			yield self.writer.writerow(self.headers)

		cursor = self.conn.cursor()
		for row in cursor.execute(self.sql):
			yield self.writer.writerow(self.format(row))

		self.conn.close()

class SSRDownloader(BaseDownloader):
	def __init__(self, db, ssrs, outfmt):
		super(SSRDownloader, self).__init__(db, ssrs, outfmt)

	@property
	def base_sql(self):
		return ("SELECT * FROM ssr INNER JOIN sequence AS s ON (s.id=ssr.sequence_id)"
				" INNER JOIN ssrmeta AS m ON (m.ssr_id=ssr.id)"
				" LEFT JOIN ssrannot AS a ON (a.ssr_id=ssr.id)")
	@property
	def headers(self):
		return ['#ID', 'Seqname', 'Seqacc', 'Start', 'End', 'Motif', 'Standmotif', \
				'Type', 'Repeats', 'Length', 'Location', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		location = self.get_location(row[16])
		stype = self.get_ssr_type(row[6])
		return (row[0], row[10], row[11], row[2], row[3], row[4], row[5], stype, row[7], \
		 		row[8], location, row[13], row[14])

	def gff_format(self, row):
		location = self.get_location(row[16])
		stype = self.get_ssr_type(row[6])
		attrs = 'ID={};Moitf={};Standardmotif={};Type={};Repeats={};Location={}'.format(row[0], \
			row[4], row[5], stype, row[7],location)
		return (row[11], 'PSMD', 'SSR', row[2], row[3], row[8], '.', '.', attrs)

class SSRTaskDownloader(BaseDownloader):
	def __init__(self, db, ssrs, outfmt):
		super(SSRTaskDownloader, self).__init__(db, ssrs, outfmt)

	@property
	def base_sql(self):
		return ("SELECT * FROM ssr INNER JOIN sequence AS s ON (s.id=ssr.sequence_id)"
				" INNER JOIN ssrmeta AS m ON (m.ssr_id=ssr.id)")

	@property
	def headers(self):
		return ['#ID', 'Seqname', 'Seqacc', 'Start', 'End', 'Motif', 'Standmotif', \
				'Type', 'Repeats', 'Length', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		stype = self.get_ssr_type(row[6])
		return (row[0], row[10], row[11], row[2], row[3], row[4], row[5], stype, row[7], \
		 		row[8], row[13], row[14])

	def gff_format(self, row):
		stype = self.get_ssr_type(row[6])
		attrs = 'ID={};Moitf={};Standardmotif={};Type={};Repeats={}'.format(row[0], \
			row[4], row[5], stype, row[7])
		return (row[11], 'PSMD', 'SSR', row[2], row[3], row[8], '.', '.', attrs)


class CSSRDownloader(BaseDownloader):
	def __init__(self, db, cssrs, outfmt):
		super(CSSRDownloader, self).__init__(db, cssrs, outfmt)

	@property
	def base_sql(self):
		return ("SELECT * FROM cssr INNER JOIN sequence AS s ON (s.id=cssr.sequence_id)"
				" INNER JOIN cssrmeta AS m ON (m.cssr_id=cssr.id)"
				" LEFT JOIN cssrannot AS a ON (a.cssr_id=cssr.id)")
	@property
	def headers(self):
		return ['#ID', 'Seqname', 'Seqacc', 'Start', 'End', 'Complexity', 'Length', \
				'Pattern', 'Location', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		location = self.get_location(row[14])
		return (row[0], row[8], row[9], row[2], row[3], row[4], row[5], row[6], location, \
				row[11], row[12])

	def gff_format(self, row):
		location = self.get_location(row[14])
		attrs = 'ID={};Complexity={};Pattern={};Location={}'.format(row[0], row[4], row[6], location)
		return (row[9], 'PSMD', 'CSSR', row[2], row[3], row[5], '.', '.', attrs)

class CSSRTaskDownloader(BaseDownloader):
	def __init__(self, db, cssrs, outfmt):
		super(CSSRTaskDownloader, self).__init__(db, cssrs, outfmt)

	@property
	def base_sql(self):
		return ("SELECT * FROM cssr INNER JOIN sequence AS s ON (s.id=cssr.sequence_id)"
				" INNER JOIN cssrmeta AS m ON (m.cssr_id=cssr.id)")

	@property
	def headers(self):
		return ['#ID', 'Seqname', 'Seqacc', 'Start', 'End', 'Complexity', 'Length', \
				'Pattern', 'Location', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		return (row[0], row[8], row[9], row[2], row[3], row[4], row[5], row[6], \
				row[11], row[12])

	def gff_format(self, row):
		attrs = 'ID={};Complexity={};Pattern={}'.format(row[0], row[4], row[6])
		return (row[9], 'PSMD', 'CSSR', row[2], row[3], row[5], '.', '.', attrs)

class ISSRTaskDownloader(BaseDownloader):
	def __init__(self, db, issrs, outfmt):
		super(ISSRTaskDownloader, self).__init__(db, issrs, outfmt)

	@property
	def base_sql(self):
		return ("SELECT * FROM issr INNER JOIN sequence AS s ON (s.id=issr.sequence_id)"
				" INNER JOIN issrmeta AS m ON (m.issr_id=issr.id)")

	@property
	def headers(self):
		return ['#ID', 'Seqname', 'Start', 'End', 'Motif', 'Standardmotif', 'Type', 'Length', \
				'Match', 'Substitution', 'Insertion', 'Deletion', 'Score', 'Sequence', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		stype = self.get_ssr_type(row[6])
		return (row[0], row[14], row[2], row[3], row[4], row[5], stype, row[7], row[8], \
				row[9], row[10], row[11], row[12], row[19], row[17], row[18])

	def gff_format(self, row):
		stype = self.get_ssr_type(row[6])
		attrs = 'ID={};Motif={};Standardmotif={};Type={};Match={};Substitution={};Insertion={};Deletion={}'.format(
			row[0], row[4], row[5], stype, row[8], row[9], row[10], row[11])
		return (row[14], 'PSMD', 'ISSR', row[2], row[3], row[12], '.', '.', attrs)

def download_ssrs(db, ssrs, ssrtype, task_id, outfmt):
	if task_id:
		outfile = '{}s_{}_{}.{}'.format(ssrtype.upper(), task_id, time.strftime("%Y%m%d-%H%M%S"), outfmt)
	else:
		outfile = '{}s_{}.{}'.format(ssrtype.upper(), time.strftime("%Y%m%d-%H%M%S"), outfmt)

	if task_id and ssrtype == 'ssr':
		loader = SSRTaskDownloader(db, ssrs, outfmt)

	if task_id and ssrtype == 'cssr':
		loader = CSSRTaskDownloader(db, ssrs, outfmt)

	elif ssrtype == 'ssr':
		loader = SSRDownloader(db, ssrs, outfmt)

	elif ssrtype == 'cssr':
		loader = CSSRDownloader(db, ssrs, outfmt)

	elif ssrtype == 'issr':
		loader = ISSRTaskDownloader(db, ssrs, outfmt)

	response = StreamingHttpResponse(
		streaming_content = loader.iter(),
		content_type='text/csv'
	)
	response['Content-Disposition'] = 'attachment; filename="{}"'.format(outfile)
	
	return response

def download_statistics(post):
	stat_type = post.get('mode')
	data_type = post.get('datatype')
	outfmt = post.get('outfmt')
	kingdom = int(post.get('kingdom', 0))
	group = int(post.get('group', 0))
	subgroup = int(post.get('subgroup', 0))
	species = int(post.get('species', 0))
	unit = post.get('unit', 'GB')

	filters = Filters()
	if species:
		filters.add('id', species)

	if subgroup:
		filters.add('category', subgroup)

	if group: 
		filters.add('category__parent', group)

	if kingdom:
		filters.add('category__parent__parent', kingdom)
	

	if filters:
		genomes = Genome.objects.select_related('category', 'category__parent', 'category__parent__parent').filter(**filters)
	else:
		genomes = Genome.objects.select_related('category', 'category__parent', 'category__parent__parent').all()

	pseudo_writer = Echo()
	if outfmt == 'csv':
		writer = csv.writer(pseudo_writer)
	else:
		writer = csv.writer(pseudo_writer, delimiter='\t')

	if stat_type == 'overview_statistics':
		def data_generator():
			yield writer.writerow(('ID', 'Kingdom', 'Group', 'Subgroup', 'Taxonomy', 'Species name',
				'Accession', 'Genome size', 'GC content', 'SSR counts', 'SSR frequency',
				'SSR density', 'Genome coverage', 'CM counts', 'CM frequency', 'CM density',
				'cSSRs%'))
			for g in genomes:
				yield writer.writerow((g.id, g.category.parent.parent.name,
					g.category.parent.name, g.category.name,
					g.taxonomy, g.species_name,
					g.download_accession,
					humanized_genome_size(g.size, unit), 
					g.gc_content,
					g.ssr_count,
					g.ssr_frequency,
					g.ssr_density,
					g.cover,
					g.cm_count,
					g.cm_frequency,
					g.cm_density,
					g.cssr_percent
				))

	elif stat_type == 'ssrtype_statistics':
		def data_generator():
			yield writer.writerow(('#Kingdom', 'Group', 'Subgroup', 'Species', 'Mono', 'Di',
				'Tri', 'Tetra', 'Penta', 'Hexa'))
			for g in genomes:
				out_row = [g.category.parent.parent.name, g.category.parent.name, g.category.name]
				sub_dir = os.path.join(*out_row)
				sub_dir = sub_dir.replace(' ', '_').replace(',', '')
				db_file = os.path.join(Config.DB_DIR, sub_dir, '{}.db'.format(g.download_accession))

				db_config = {
					'ENGINE': 'django.db.backends.sqlite3',
					'NAME': db_file
				}

				out_row.append(g.species_name)
				
				with in_database(db_config):
					res = Summary.objects.get(option='ssr_types')
					ssr_counts = json.loads(res.content)
				
				genome_size = g.size

				for i, t in enumerate(['Mono', 'Di', 'Tri', 'Tetra', 'Penta', 'Hexa']):
					count = ssr_counts.get(t, 0)

					print(data_type)

					if data_type == 'ssr_counts':
						out_row.append(count)

					elif data_type == 'ssr_length':
						out_row.append(count*(i+1))

					elif data_type == 'ssr_frequency':
						out_row.append(count/(genome_size/1000000))

					elif data_type == 'ssr_density':
						out_row.append(count*(i+1)/(genome_size/1000000))

				print(out_row)

				yield writer.writerow(out_row)

	elif stat_type == 'motif_statistics':
		pass

	elif stat_type == 'genic_statistics':
		pass


	response = StreamingHttpResponse(
		streaming_content = data_generator(),
		content_type='text/csv'
	)
	response['Content-Disposition'] = 'attachment; filename="{}.{}"'.format(stat_type, outfmt)
	
	return response

				
	