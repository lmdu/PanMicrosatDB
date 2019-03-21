import csv
import time
import sqlite3

from django.http import StreamingHttpResponse

class Echo:
	def write(self, value):
		return value

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
		if self.outfmt == 'csv':
			self.writer = csv.writer(pseudo_writer)
		else:
			self.writer = csv.writer(pseudo_writer, delimiter='\t')

		self.locations = {1: 'CDS', 2: 'exon', 3: '3UTR', 4: 'intron', 5: '5UTR'}
		self.ssrtypes = {1: 'Mono', 2: 'Di', 3: 'Tri', 4: 'Tetra', 5: 'Penta', 6: 'Hexa'}

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
		self.base_sql = ("SELECT * FROM ssr INNER JOIN sequence AS s ON (s.id=ssr.sequence_id)"
				" INNER JOIN ssrmeta AS m ON (m.ssr_id=ssr.id)"
				" LEFT JOIN ssrannot AS a ON (a.ssr_id=ssr.id)")

		self.headers = ['#ID', 'Seqname', 'Seqacc', 'Start', 'End', 'Motif', 'Standmotif', \
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

class CSSRDownloader(BaseDownloader):
	def __init__(self, db, cssrs, outfmt):
		super(CSSRDownloader, self).__init__(db, cssrs, outfmt)
		self.base_sql = ("SELECT * FROM cssr INNER JOIN sequence AS s ON (s.id=cssr.sequence_id)"
				" INNER JOIN cssrmeta AS m ON (m.cssr_id=cssr.id)"
				" LEFT JOIN cssrannot AS a ON (a.cssr_id=cssr.id)")

		self.headers = ['#ID', 'Seqname', 'Seqacc', 'Start', 'End', 'Complexity', 'Length', \
						'Pattern', 'Location', 'Leftflank', 'Rightflank']

	def tab_format(self, row):
		location = self.get_location(row[14])
		return (row[0], row[8], row[9], row[2], row[3], row[4], row[5], row[6], location, \
				row[11], row[12])

	def gff_format(self, row):
		location = self.get_location(row[14])
		attrs = 'ID={};Complexity={};Pattern={};Location={}'.format(row[0], row[4], row[6], location)
		return (row[9], 'PSMD', 'CSSR', row[2], row[3], row[5], '.', '.', attrs)

def download_ssrs(db, ssrs, ssrtype, outfmt):
	outfile = '{}s-{}.{}'.format(ssrtype.upper(), time.strftime("%Y%m%d-%H%M%S"), outfmt)

	if ssrtype == 'ssr':
		loader = SSRDownloader(db, ssrs, outfmt)

	elif ssrtype == 'cssr':
		loader = CSSRDownloader(db, ssrs, outfmt)

	response = StreamingHttpResponse(
		streaming_content = loader.iter(),
		content_type='text/csv'
	)
	response['Content-Disposition'] = 'attachment; filename="{}"'.format(outfile)
	
	return response