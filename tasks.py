import os
import json
import sqlite3
import requests

from celery import shared_task, Task

from .models import Genome
from .config import Config
from .thirds import kseq, tandem
from .thirds.motifs import StandardMotif

TABLE_SQL = """
CREATE TABLE ssr(
	id INTEGER PRIMARY KEY,
	seqid TEXT,
	start INTEGER,
	end INTEGER,
	motif TEXT,
	standard_motif TEXT,
	ssr_type INTEGER,
	repeats INTEGER,
	length INTEGER,
	left TEXT,
	right TEXT
);

CREATE TABLE cssr(
	id INTEGER PRIMARY KEY,
	seqid TEXT,
	start INTEGER,
	end INTEGER,
	complexity INTEGER,
	length INTEGER,
	structure TEXT,
	left TEXT,
	right TEXT
);

CREATE TABLE issr(
	id INTEGER PRIMARY KEY,
	seqid TEXT,
	start INTEGER,
	end INTEGER,
	motif TEXT,
	standard_motif TEXT,
	ssr_type INTEGER,
	length INTEGER,
	match INTEGER,
	substitution INTEGER,
	insertion INTEGER,
	deletion INTEGER,
	score INTEGER,
	left TEXT,
	right TEXT
)
"""

def download_fasta_file(tid, url):
	'''
	@param tid, task ID
	@param url, URL of fasta file
	'''
	if url.endswith('.gz'):
		outname = '{}.fa.gz'.format(tid)
	else:
		outname = '{}.fa'.format(tid)

	down_request = json.dumps({
		'id': '',
		'jsonrpc': '2.0',
		'method': 'aria2.addUri',
		'params': [[url], {'dir': Config.TASK_FASTA_DIR, 'out': outname}]
	})
	response = requests.post(url=Config.ARIA2C_RPC, data=down_request)

	result = None
	if response.status_code == requests.codes.ok:
		result = response.json()['result']

	check_request = json.dumps({
		'id': '',
		'jsonrpc': '2.0',
		'method': 'aria2.tellStatus',
		'params': [result]
	})

	while 1:
		response = requests.post(url=Config.ARIA2C_RPC, data=check_request)

		if response.status_code == requests.codes.ok:
			status = response.join()['result']['status']

			if status == 'complete' or status == 'error':
				break
		else:
			break

	return os.path.join(Config.TASK_FASTA_DIR, outname)

def get_selected_fasta_file(gid):
	'''
	@param gid, genome ID
	'''
	try:
		genome = Genome.objects.get(pk=gid)
	except Genome.DoesNotExist:
		return None
	
	sub_dir = os.path.join(genome.category.parent.parent.name, genome.category.parent.name, genome.category.name)
	sub_dir = sub_dir.replace(' ', '_').replace(',', '')
	fa_file = os.path.join(Config.FASTA_DIR, sub_dir, '{}.fa.gz'.format(genome.download_accession))

	return fa_file

def make_fasta_file(tid, seqs):
	'''
	@param tid, task ID
	'''
	fa_file = os.path.join(Config.TASK_FASTA_DIR, '{}.fa'.format(tid))
	with open(fa_file, 'w') as fw:
		fw.write(seqs)
	return fa_file

def get_flank_seq(seq, start, end, flank):
	s = start - flank - 1
	if s < 0:
		s = 0

	left = seq[s:start-1]
	right = seq[end:end+flank]

	return (left, right)

def search_for_ssr(fasta_file, min_repeats, standard_level, flank_len):
	standard_motifs = StandardMotif(standard_level)
	for seqid, seq in kseq.fasta(fasta_file):
		ssrs = tandem.search_ssr(seq, min_repeats)
		if not ssrs:
			continue

		for ssr in ssrs:
			smotif = standard_motifs.standard(ssr[0])
			left, right = get_flank_seq(seq, ssr[3], ssr[4], flank_len)
			yield [None, seqid, ssr[3], ssr[4], ssr[0], smotif, ssr[1], ssr[2], ssr[5], left, right]

	kseq.close_fasta()

def concatenate_cssr(seqid, seq, cssrs, flank_len):
	start = cssrs[0][3]
	end = cssrs[-1][4]
	complexity = len(cssrs)
	length = sum(cssr[5] for cssr in cssrs)

	components = []
	for i, cssr in enumerate(cssrs):
		components.append("({}){}".format(cssr[0], cssr[2]))

		if i < len(cssrs) - 1:
			components.append(seq[cssr[4]:cssrs[i+1][3]-1])

	structure = "".join(components)

	left, right = get_flank_seq(seq, start, end, flank_len)
	
	return (None, seqid, start, end, complexity, length, structure, left, right)

def search_for_cssr(fasta_file, min_repeats, dmax, flank_len):
	for seqid, seq in kseq.fasta(fasta_file):
		ssrs = tandem.search_ssr(seq, min_repeats)
		if not ssrs:
			continue

		cssrs = [ssrs[0]]
		for ssr in ssrs[1:]:
			d = ssr[3] - cssrs[-1][4] - 1
			if d <= dmax:
				cssrs.append(ssr)
			else:
				if len(cssrs) > 1:
					yield concatenate_cssr(seqid, seq, cssrs, flank_len)

				cssrs = [ssr]

		if len(cssrs) > 1:
			yield concatenate_cssr(seqid, seq, cssrs, flank_len)

	kseq.close_fasta()

def search_for_issr(fasta_file, seed_repeat, seed_len, max_edits, mis_penalty, gap_penalty, min_score, standard_level, flank_len):
	standard_motifs = StandardMotif(standard_level)
	for seqid, seq in kseq.fasta(fasta_file):
		issrs = tandem.search_issr(seq, seed_repeat, seed_len, max_edits, mis_penalty, gap_penalty, min_score, 500)
		if not issrs:
			continue

		for issr in issrs:
			smotif = standard_motifs.standard(issr[0])
			letf, right = get_flank_seq(seq, issr[2], issr[3], flank_len)
			yield [None, seqid, issr[2], issr[3], issr[0], smotif, issr[4], issr[5], issr[6], issr[7], issr[8], issr[9], left, right]

	kseq.close_fasta()


class BaseTask(Task):
	_db = None
	def on_failure(self, exc, task_id, args, kwargs, einfo):
		print(exc)

	def on_success(self, retval, task_id, args, kwargs):
		print('success')

	@property
	def db(self):
		if self._db is None:
			db_file = os.path.join(Config.TASK_RESULT_DIR, '{}.db'.format(self.request.id))
			self._db = sqlite3.connect(db_file)
			self._db.cursor().executescript(TABLE_SQL)
		return self._db

@shared_task(bind=True, base=BaseTask)
def search_ssrs(self, params):
	task_id = self.request.id

	if params['input_type'] == 'select':
		fasta_file = get_selected_fasta_file(int(params['select_species']))

	elif params['input_type'] == 'input':
		fasta_file = make_fasta_file(task_id, params['input_seqs'])

	elif params['input_type'] == 'url':
		fasta_file = download_fasta_file(task_id, params['input_url'])

	flank_length = int(params['flank_len'])
	email_addr = params['email']

	if params['ssr_type'] == 'ssr':
		sql = "INSERT INTO ssr VALUES (?,?,?,?,?,?,?,?,?,?,?)"
		min_repeats = [int(rep) for rep in params['min_reps'].split('-')]
		standard_level = int(params['level'])
		ssrs = search_for_ssr(fasta_file, min_repeats, standard_level, flank_length)
		self.db.cursor().executemany(sql, ssrs)

	elif params['ssr_type'] == 'cssr':
		sql = "INSERT INTO ssr VALUES (?,?,?,?,?,?,?,?,?)"
		min_repeats = [int(rep) for rep in params['min_reps'].split('-')]
		dmax = int(params['dmax'])
		cssrs = search_for_cssr(fasta_file, min_repeats, dmax, flank_length)
		self.db.cursor().executemany(sql, cssrs)

	elif params['ssr_type'] == 'issr':
		sql = "INSERT INTO issr VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
		seed_repeat = int(params['min_seed_rep'])
		seed_len = int(params['min_seed_len'])
		max_edits = int(params['max_edits'])
		mis_penalty = int(params['mis_penalty'])
		gap_penalty = int(params['gap_penalty'])
		min_score = int(params['min_score'])
		standard_level = int(params['level'])
		issrs = search_for_issr(fasta_file, seed_repeat, seed_len, max_edits, mis_penalty, gap_penalty, min_score, standard_level, flank_len)
		self.db.cursor().executemany(sql, issrs)
