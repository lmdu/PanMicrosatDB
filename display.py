import re

from .utils import *
from .router import in_database

from django.http import JsonResponse

class BaseDisplay(object):
	'''Show SSRs in Datatable
	@param db, db config used for in_database to switch database connection
	@param post, django request.POST parameters
	'''
	def __init__(self, db, post):
		self.db = db
		self.post = post
		self.total = 0
		self.filtered_total = 0
		self.data = []
		
		#datatable parameters
		self.dt = get_datatable_params(post)

		#get ssrs records
		self.get_data()

	@property
	def model(self):
		return None

	@property
	def filters(self):
		return {}

	def format_row(self, row):
		return row

	def get_data(self):
		with in_database(self.db):
			self.ssrs = self.model.all()
			self.total = self.ssrs.count()
			if self.filters:
				self.ssrs = self.model.filter(**self.filters)
				self.filtered_total = self.ssrs.count()
			else:
				self.filtered_total = self.total

			#set orders
			if self.dt.sortdir == 'asc':
				self.ssrs = self.ssrs.order_by(self.dt.colname)
			else:
				self.ssrs = self.ssrs.order_by('-{}'.format(self.dt.colname))

			self.data = [self.format_row(ssr) for ssr in self.ssrs[self.dt.start:self.dt.start+self.dt.length]]

	def get_response(self):
		return JsonResponse({
			'draw': self.dt.draw,
			'recordsTotal': self.total,
			'recordsFiltered': self.filtered_total,
			'data': self.data
		})

class SSRDisplay(BaseDisplay):
	def __init__(self, db, post):
		super(SSRDisplay, self).__init__(db, post)

	@property
	def model(self):
		return SSR.objects.select_related()

	@property
	def filters(self):
		return get_ssr_request_filters(self.post)

	def format_row(self, ssr):
		try:
			location = ssr.ssrannot.get_location_display()
		except:
			location = 'N/A'

		return (ssr.id, ssr.sequence.accession, ssr.sequence.name, ssr.start, \
				ssr.end, colored_seq(ssr.motif), colored_seq(ssr.standard_motif), \
				ssr.get_ssr_type_display(), ssr.repeats, ssr.length, location)

class SSRTaskDisplay(SSRDisplay):
	def __init__(self, db, post):
		super(SSRTaskDisplay, self).__init__(db, post)

	def format_row(self, ssr):
		return (ssr.id, ssr.sequence.name, ssr.start, ssr.end, colored_seq(ssr.motif), \
				colored_seq(ssr.standard_motif), ssr.get_ssr_type_display(), ssr.repeats, \
				ssr.length)

class CSSRDisplay(BaseDisplay):
	def __init__(self, db, post):
		super(CSSRDisplay, self).__init__(db, post)

	@property
	def model(self):
		return CSSR.objects.select_related()

	@property
	def filters(self):
		return get_cssr_request_filters(self.post)

	def format_row(self, cssr):
		try:
			location = cssr.cssrannot.get_location_display()
		except:
			location = 'N/A'

		pattern = colored_cssr_pattern(cssr.structure)
		pattern = re.sub(r'(\d+)', lambda m: '<sub>'+m.group(0)+'</sub>', pattern)

		return (cssr.id, cssr.sequence.accession, cssr.sequence.name, \
			cssr.start, cssr.end, cssr.complexity, cssr.length, pattern, location)

class BaseDetail(objects):
	def __init__(self, db, post):
		self.db = db
		self.ssr_id = int(post.get('ssr_id'))
		self.primer_settings = get_primer_setttings(post)
		#get detailed information
		self.get_detail()

	@property
	def model(self):
		return SSR.objects

	@property
	def seq(self):
		return "".join([self.ssr.motif]*self.ssr.repeats)

	def get_detail(self):
		with in_database(self.db):
			self.ssr = self.model.get(id=self.ssr_id)
			self.flank = self.ssr.ssrmeta
			try:
				self.annot = self.ssr.ssrannot
				self.gene = self.annot.gene
			except:
				self.annot = None
				self.gene = None

	def format_nucleotide(base):
		return """<div class="sequence-nucleotide">
					<div class="base-row sequence-box">
						<span class="nucleobase {0}">{0}</span>
					</div>
					<div class="meta-row sequence-box">
						<span class="meta-info"></span>
					</div>
				</div>""".format(base)

	def format_target(base):
		return """<div class="sequence-nucleotide">
					<div class="base-row sequence-box">
						<span class="nucleobase-target {0}">{0}</span>
					</div>
					<div class="meta-row sequence-box">
						<span class="meta-info">{1}</span>
					</div>
				</div>""".format(base)

	def get_sequence(self):
		html = []

		for b in self.flank.left_flank:
			html.append(self.format_nucleotide(b))

		#if type_ == 'ssr':
		#	ssr_seq = "".join([ssr.motif]*ssr.repeats)
		#elif type_ == 'cssr':
		#	ssr_seq = cssr_pattern_to_seq(ssr.structure)

		for i,b in enumerate(self.seq):
			if i == 0:
				html.append(self.format_target(b, ssr.start))
			elif i + 1 == len(self.seq):
				html.append(self.format_target(b, ssr.end))
			else:
				html.append(self.format_target(b, ''))

		for b in self.flank.right_flank:
			html.append(self.format_nucleotide(b))

		return ''.join(html)

	def get_location(self):
		html = '<tr><td class="text-center" colspan="4">N/A</td><td>Intergenic</td></tr>'
		
		if self.annot:
			loc = self.annot.get_location_display()
			gid = self.gene.gid
			name = self.gene.name
			biotype = self.gene.biotype
			dbxref = self.gene.dbxref
			html = "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(gid, name, biotype, dbxref, loc)
		
		return html

	def get_primer(self):
		res = primer3.bindings.designPrimers({
			'SEQUENCE_ID': self.ssr_id,
			'SEQUENCE_TEMPLATE': "{}{}{}".format(self.flank.left_flank, self.seq, self.flank.right_flank),
			'SEQUENCE_TARGET': [len(self.flank.left_flank), len(self.seq)],
			'SEQUENCE_INTERNAL_EXCLUDED_REGION': [len(self.flank.left_flank), len(self.seq)]
		}, self.primer_settings)

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

				html = """
				<tr><td class="align-middle" rowspan="2">{}</td><td>Forward</td><td>{}</td><td>{}</td>
				<td>{}</td><td>{}</td><td class="align-middle" rowspan="2">{}</td></tr>
				<tr><td>Reverse</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>
				"""
				primers.append(html.format(num, forward, tm1, gc1, stab1, product, reverse, tm2, gc2, stab2))

			primers = "".join(primers)
		else:
			primers = '<tr><td class="text-center" colspan="7">N/A</td></tr>'

		return primers

	def get_response(self):
		return JsonResponse(dict(
			seq = self.get_sequence(), 
			location = self.get_location(),
			primer = self.get_primer()
		))

