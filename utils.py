import re
import csv
from dynamic_db_router import in_database
from django.http import StreamingHttpResponse

def colored_sequence(seq, start, end):
	pass

def colored_seq(seq):
	'''
	colored the base from given dna sequence
	'''
	return ''.join('<span class="B {0}">{0}</span>'.format(b)  for b in seq)

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

	def ssrs_iter():
		yield writer.writerow(['ID', 'Seqacc', 'Seqname', 'Start', 'End', 'Motif', 'Standmotif', 'Type', 'Repeats', 'Length', 'Location', 'Leftflank', 'Rightflank'])

		with in_database(db):
			for ssr in ssrs:
				yield writer.writerow(make_table(ssr))

	
	response = StreamingHttpResponse(
		streaming_content = ssrs_iter(),
		content_type='text/csv'
	)
	response['Content-Disposition'] = 'attachment; filename="{}"'.format(outfile)
	
	return response

