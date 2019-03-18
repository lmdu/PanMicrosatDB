import os
import json
import requests

from celery import shared_task

from .models import Genome
from .config import Config

TABLE_SQL = """
CREATE TABLE ssr(
	id INTEGER PRIMARY KEY,
	seqname INTEGER,
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
	seqname INTEGER,
	start INTEGER,
	end INTEGER,
	complexity INTEGER,
	length INTEGER,
	structure TEXT,
	left TEXT,
	right TEXT
);
"""

def download_fasta_file(tid, url):
	'''
	@para tid, task ID
	@para url, URL of fasta file
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
	@para gid, genome ID
	'''
	try:
		genome = Genome.objects.get(pk=gid)
	except Genome.DoesNotExist:
		return None
	
	sub_dir = os.path.join(genome.category.parent.parent.name, genome.category.parent.name, genome.category.name)
	sub_dir = sub_dir.replace(' ', '_').replace(',', '')
	db_file = os.path.join(Config.DB_DIR, sub_dir, '{}.db'.format(genome.download_accession))

	return db_file

def make_fasta_file(tid, seqs):
	'''
	@para tid, task ID
	'''
	fa_file = os.path.join(Config.TASK_FASTA_DIR, '{}.fa'.format(tid))
	with open(fa_file, 'w') as fw:
		fw.write(fa_file)
	return fa_file

@shared_task(bind=True)
def search_ssrs(self):
	db_file = os.path.join(Config.TASK_RESULT_DIR, )
	conn = sqlite3.connect(db_file)
	cursor = conn.cursor()
	cursor.executescript(TABLE_SQL)

