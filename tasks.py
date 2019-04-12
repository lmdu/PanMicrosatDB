import os
import json
import time
import sqlite3
import requests

from django.core.mail import send_mail
from celery import shared_task, Task

from .models import Genome, Job
from .config import Config
from .thirds import kseq, tandem
from .thirds.motifs import StandardMotif

TABLE_SQL = """
CREATE TABLE sequence(
	id INTEGER PRIMARY KEY,
	name TEXT,
	accession TEXT
);
CREATE TABLE ssr(
	id INTEGER PRIMARY KEY,
	sequence_id INTEGER,
	start INTEGER,
	end INTEGER,
	motif TEXT,
	standard_motif TEXT,
	ssr_type INTEGER,
	repeats INTEGER,
	length INTEGER
);
CREATE TABLE ssrmeta(
	ssr_id INTEGER PRIMARY KEY,
	left_flank TEXT,
	right_flank TEXT
);
CREATE TABLE cssr(
	id INTEGER PRIMARY KEY,
	sequence_id INTEGER,
	start INTEGER,
	end INTEGER,
	complexity INTEGER,
	length INTEGER,
	structure TEXT
);

CREATE TABLE cssrmeta(
	cssr_id INTEGER PRIMARY KEY,
	left_flank TEXT,
	right_flank TEXT
);
CREATE TABLE issr(
	id INTEGER PRIMARY KEY,
	sequence_id INTEGER,
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
	score INTEGER
);
CREATE TABLE issrmeta(
	issr_id INTEGER PRIMARY KEY,
	left_flank TEXT,
	right_flank TEXT,
	self_seq TEXT
);
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

	if response.status_code == requests.codes.ok:
		result = response.json()['result']
	else:
		raise Exception("Failed to download {}".format(url))

	check_request = json.dumps({
		'id': '',
		'jsonrpc': '2.0',
		'method': 'aria2.tellStatus',
		'params': [result]
	})

	while 1:
		time.sleep(1)
		response = requests.post(url=Config.ARIA2C_RPC, data=check_request)

		if response.status_code == requests.codes.ok:
			status = response.json()['result']['status']

			if status == 'complete':
				break
			elif status == 'error':
				raise Exception(response.json()['result']['errorMessage'])
		else:
			raise Exception("Failed to get task ({}) status".format(tid))

	return os.path.join(Config.TASK_FASTA_DIR, outname)

def get_selected_fasta_file(gid):
	'''
	@param gid, genome ID
	'''
	try:
		genome = Genome.objects.get(pk=gid)
	except Genome.DoesNotExist:
		raise Exception("Fasta file does not exist")
	
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

def upload_fasta_file(tid, infile):
	if infile.name.endswith('.gz'):
		destname = '{}.fa.gz'.format(tid)
	else:
		destname = '{}.fa'.format(tid)

	fa_file = os.path.join(Config.TASK_FASTA_DIR, destname)

	with open(fa_file, 'wb+') as fw:
		for chunk in infile.chunks():
			fw.write(chunk)

	return fa_file


def get_flank_seq(seq, start, end, flank):
	s = start - flank - 1
	if s < 0:
		s = 0

	left = seq[s:start-1]
	right = seq[end:end+flank]

	return (left, right)

def search_for_ssr(db, fasta_file, min_repeats, standard_level, flank_len):
	standard_motifs = StandardMotif(standard_level)
	seq_num = 0
	ssr_num = 1
	seq_sql = "INSERT INTO sequence VALUES (?,?,?)"
	for seqid, seq in kseq.fasta(fasta_file):
		seq_num += 1
		db.cursor().execute(seq_sql, (seq_num, seqid, seqid))

		ssrs = tandem.search_ssr(seq, min_repeats)
		if not ssrs:
			continue

		ssrs = [(ssr_num+idx, seq_num, ssr[3], ssr[4], ssr[0], standard_motifs.standard(ssr[0]), ssr[1], ssr[2], ssr[5]) for idx, ssr in enumerate(ssrs)]
		ssr_num += len(ssrs)
		ssr_sql = "INSERT INTO ssr VALUES (?,?,?,?,?,?,?,?,?)"
		db.cursor().executemany(ssr_sql, ssrs)

		def extract_flank(x):
			left, right = get_flank_seq(seq, x[2], x[3], flank_len)
			return (x[0], left, right)
			
		flank_sql = "INSERT INTO ssrmeta VALUES (?,?,?)"
		db.cursor().executemany(flank_sql, map(extract_flank, ssrs))

def concatenate_cssr(seqid, seq, cssrs):
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
	
	return [None, seqid, start, end, complexity, length, structure]

def search_for_cssr(db, fasta_file, min_repeats, dmax, flank_len):
	seq_num = 0
	cm_num = 0
	seq_sql = "INSERT INTO sequence VALUES (?,?,?)"
	for seqid, seq in kseq.fasta(fasta_file):
		seq_num += 1
		db.cursor().execute(seq_sql, (seq_num, seqid, seqid))

		ssrs = tandem.search_ssr(seq, min_repeats)
		if not ssrs:
			continue

		cms = []
		cssrs = [ssrs[0]]
		for ssr in ssrs[1:]:
			d = ssr[3] - cssrs[-1][4] - 1
			if d <= dmax:
				cssrs.append(ssr)
			else:
				if len(cssrs) > 1:
					cm = concatenate_cssr(seq_num, seq, cssrs)
					cm_num += 1
					cm[0] = cm_num
					cms.append(cm)

				cssrs = [ssr]

		if len(cssrs) > 1:
			cm = concatenate_cssr(seq_num, seq, cssrs)
			cm_num += 1
			cm[0] = cm_num
			cms.append(cm)
			
		cm_sql = "INSERT INTO cssr VALUES (?,?,?,?,?,?,?)"
		db.cursor().executemany(cm_sql, cms)

		def extract_flank(cm):
			left, right = get_flank_seq(seq, cm[2], cm[3], flank_len)
			return (cm[0], left, right)
		flank_sql = "INSERT INTO cssrmeta VALUES (?,?,?)"
		db.cursor().executemany(flank_sql, map(extract_flank, cms))

def search_for_issr(db, fasta_file, seed_repeat, seed_len, max_edits, mis_penalty, \
					gap_penalty, min_score, standard_level, flank_len):
	standard_motifs = StandardMotif(standard_level)
	seq_num = 0
	issr_num = 1
	seq_sql = "INSERT INTO sequence VALUES (?,?,?)"
	for seqid, seq in kseq.fasta(fasta_file):
		seq_num += 1
		db.cursor().execute(seq_sql, (seq_num, seqid, seqid))

		issrs = tandem.search_issr(seq, seed_repeat, seed_len, max_edits, mis_penalty, \
									gap_penalty, min_score, 500)
		if not issrs:
			continue

		issrs = [(issr_num+idx, seq_num, issr[2], issr[3], issr[0], standard_motifs.standard(issr[0]), issr[1], \
				 issr[4], issr[5], issr[6], issr[7], issr[8], issr[9]) for idx,issr in enumerate(issrs)]
		issr_num += len(issrs)
		issr_sql = "INSERT INTO issr VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
		db.cursor().executemany(issr_sql, issrs)

		def extract_flank(issr):
			left, right = get_flank_seq(seq, issr[2], issr[3], flank_len)
			return (issr[0], left, right, seq[issr[2]-1:issr[3]])

		flank_sql = "INSERT INTO issrmeta VALUES (?,?,?,?)"
		db.cursor().executemany(flank_sql, map(extract_flank, issrs))

class BaseTask(Task):
	_db = None
	def after_return(self, status, retval, task_id, args, kwargs, einfo):
		email = args[0]['email']
		if email:
			title = 'Task completed'
			content = 'View task results: http://big.cdu.edu.cn/psmd/task/{}'.format(task_id)
			send_mail(title, content, 'lmdu@foxmail.com', [email])

		self.db.commit()

	def on_failure(self, exc, task_id, args, kwargs, einfo):
		Job.objects.filter(job_id=task_id).update(status=3, message=str(einfo))

	def on_success(self, retval, task_id, args, kwargs):
		Job.objects.filter(job_id=task_id).update(status=2)

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

	#change job status
	Job.objects.filter(job_id=task_id).update(status=1)

	if params['input_type'] == 'select':
		fasta_file = get_selected_fasta_file(int(params['select_species']))

	elif params['input_type'] == 'input':
		fasta_file = make_fasta_file(task_id, params['input_seqs'])

	elif params['input_type'] == 'upload':
		fasta_file = params['input_file']

	elif params['input_type'] == 'url':
		fasta_file = download_fasta_file(task_id, params['input_url'])

	flank_length = int(params['flank_len'])
	email_addr = params['email']

	if params['ssr_type'] == 'ssr':
		min_repeats = [int(rep) for rep in params['min_reps'].split('-')]
		standard_level = int(params['level'])
		search_for_ssr(self.db, fasta_file, min_repeats, standard_level, flank_length)

	elif params['ssr_type'] == 'cssr':
		min_repeats = [int(rep) for rep in params['min_reps'].split('-')]
		dmax = int(params['dmax'])
		search_for_cssr(self.db, fasta_file, min_repeats, dmax, flank_length)

	elif params['ssr_type'] == 'issr':
		seed_repeat = int(params['min_seed_rep'])
		seed_len = int(params['min_seed_len'])
		max_edits = int(params['max_edits'])
		mis_penalty = int(params['mis_penalty'])
		gap_penalty = int(params['gap_penalty'])
		min_score = int(params['min_score'])
		standard_level = int(params['level'])
		search_for_issr(self.db, fasta_file, seed_repeat, seed_len, max_edits, mis_penalty, \
		 gap_penalty, min_score, standard_level, flank_length)
