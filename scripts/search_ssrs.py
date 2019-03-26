import os
import sys
import csv
import gzip
import time
import json
import numpy
import signal
import shutil
import sqlite3
import itertools
import collections
import multiprocessing

from ..thirds import kseq, ncls, tandem
from ..thirds.motif import StandardMotif
from ..config import Config

def make_folder(folder):
	if not os.path.exists(folder):
		os.makedirs(folder)

def concatenate_cssr(seqid, seq, cssrs):
	start = cssrs[0][3]
	end = cssrs[-1][4]
	complexity = len(cssrs)
	#length = sum(cssr[5] for cssr in cssrs)
	length = end - start + 1

	components = []
	for i, cssr in enumerate(cssrs):
		components.append("({}){}".format(cssr[0], cssr[2]))

		if i < len(cssrs) - 1:
			components.append(seq[cssr[4]:cssrs[i+1][3]-1])

	structure = "".join(components)
	return (None, seqid, start, end, complexity, length, structure)

class Data(dict):
	def __getattr__(self, name):
		try:
			return self[name]
		except KeyError:
			raise AttributeError(name)

	def __setattr__(self, name, val):
		self[name] = val

def gff_parser(annot_file):
	with gzip.open(annot_file, 'rt') as fh:
		for line in fh:
			if line[0] == '#': continue
			cols = line.strip().split('\t')
			record = Data(
				seqid = cols[0],
				feature = cols[2].upper(),
				start = int(cols[3]),
				end = int(cols[4]),
				attrs = Data()
			)
			
			for item in cols[-1].split(';'):
				if not item:
					continue
				
				name, value = item.split('=')
				record.attrs[name.strip().upper()] = value
			
			yield record

def get_gff_coordinate(gff_file):
	father = None
	exons = []

	parents = {}

	for r in gff_parser(gff_file):
		if r.feature == 'REGION':
			continue

		elif r.feature == 'GENE':
			parents[r.attrs.ID] = r.attrs.ID
			continue

		elif r.feature == 'CDS':
			if 'PARENT' in r.attrs:
				yield (r.seqid, r.start, r.end, 'CDS', parents[r.attrs.PARENT])
			else:
				yield (r.seqid, r.start, r.end, 'CDS', r.attrs.ID)
		
		elif r.feature == 'FIVE_PRIME_UTR':
			if 'PARENT' in r.attrs:
				yield (r.seqid, r.start, r.end, '5UTR', parents[r.attrs.PARENT])
			else:
				yield (r.seqid, r.start, r.end, '5UTR', r.attrs.ID)

		elif r.feature == 'THREE_PRIME_UTR':
			if 'PARENT' in r.attrs:
				yield (r.seqid, r.start, r.end, '3UTR', parents[r.attrs.PARENT])
			else:
				yield (r.seqid, r.start, r.end, '3UTR', r.attrs.ID)
		
		elif r.feature == 'EXON':
			try:
				mother = r.attrs.PARENT
			except AttributeError:
				continue

			if father == mother:
				exons.append((r.seqid, r.start, r.end, 'exon', parents[r.attrs.PARENT]))
			else:
				if exons:
					exons = sorted(exons, key=lambda x: x[2])
					for idx, exon in enumerate(exons):
						yield exon

						if idx < len(exons)-1:
							start = exon[2] + 1
							end = exons[idx+1][1] - 1
							yield (exons[0][0], start, end, 'intron', parents[r.attrs.PARENT])
				
				exons = [(r.seqid, r.start, r.end, 'exon', parents[r.attrs.PARENT])]
				father = mother
		
		else:
			if 'ID' in r.attrs:
				try:
					parents[r.attrs.ID] = parents[r.attrs.PARENT]
				except:
					parents[r.attrs.ID] = r.attrs.ID

	exons = sorted(exons, key=lambda x: x[2])
	
	for idx, exon in enumerate(exons):
		yield exon

		if idx < len(exons)-1:
			start = exon[2] + 1
			end = exons[idx+1][1] - 1
			yield (exons[0][0], start, end, 'intron', exons[0][4])

TABLE_SQL = """
CREATE TABLE sequence(
	id INTEGER,
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
CREATE TABLE gene(
	id INTEGER PRIMARY KEY,
	sequence_id INTEGER,
	start INTEGER,
	end INTEGER,
	gid TEXT,
	name TEXT,
	biotype TEXT,
	dbxref TEXT
);
CREATE TABLE ssrannot(
	ssr_id INTEGER PRIMARY KEY,
	gene_id INTEGER,
	location INTEGER
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
CREATE TABLE cssrannot(
	cssr_id INTEGER PRIMARY KEY,
	gene_id INTEGER,
	location INTEGER
);
CREATE TABLE summary(
	id INTEGER PRIMARY KEY,
	option TEXT,
	content TEXT
);
"""

INDEX_SQL = """
CREATE INDEX seq_name ON sequence (name);
CREATE INDEX seq_acc ON sequence (accession);

CREATE INDEX ssr_seq_id ON ssr (sequence_id);
CREATE INDEX ssr_start ON ssr (start);
CREATE INDEX ssr_end ON ssr (end);
CREATE INDEX ssr_motif ON ssr (motif);
CREATE INDEX ssr_smotif ON ssr (standard_motif);
CREATE INDEX ssr_stype ON ssr (ssr_type);
CREATE INDEX ssr_rep ON ssr (repeats);
CREATE INDEX ssr_len ON ssr (length);

CREATE INDEX ssr_annot_gene_id ON ssrannot (gene_id);
CREATE INDEX ssr_annot_location ON ssrannot (location);
CREATE INDEX ssr_annot_ssr_gene ON ssrannot (ssr_id, gene_id);
CREATE INDEX ssr_annot_ssr_gene_loc ON ssrannot (ssr_id, gene_id, location);

CREATE INDEX cssr_seq_id ON cssr (sequence_id);
CREATE INDEX cssr_start ON cssr (start);
CREATE INDEX cssr_end ON cssr (end);
CREATE INDEX cssr_cplx ON cssr (complexity);
CREATE INDEX cssr_len ON cssr (length);

CREATE INDEX cssr_annot_gene_id ON cssrannot (gene_id);
CREATE INDEX cssr_annot_location ON cssrannot (location);
CREATE INDEX cssr_annot_cssr_gene ON cssrannot (cssr_id, gene_id);
CREATE INDEX cssr_annot_cssr_gene_loc ON cssrannot (cssr_id, gene_id, location);
"""

WORK_DIR = Config.ROOT_DIR
DB_DIR = os.path.join(WORK_DIR, 'dbs')
FA_DIR = os.path.join(WORK_DIR, 'fastas')
AR_DIR = os.path.join(WORK_DIR, 'assemblyreports')
GFF_DIR = os.path.join(WORK_DIR, 'gffs')


def search_for_ssrs(acc, info):
	#standard motif
	motifs = StandardMotif(3)

	sub_dir = os.path.join(*info[3:6]).replace(' ', '_')
	out_dir = os.path.join(DB_DIR, sub_dir)
	make_folder(out_dir)

	db_file = os.path.join(out_dir, '{}.db'.format(acc))
	fa_file = os.path.join(FA_DIR, sub_dir, '{}.fna.gz'.format(acc))
	ar_file = os.path.join(AR_DIR, sub_dir, '{}.assembly_report.txt'.format(acc))
	gff_file = os.path.join(GFF_DIR, sub_dir, '{}.gff.gz'.format(acc))

	#if database file exists, remove and redo search for SSRs
	if os.path.exists(db_file):
		os.remove(db_file)
	
	#connect to database and create tables
	conn = sqlite3.connect(db_file)
	cursor = conn.cursor()
	cursor.executescript(TABLE_SQL)

	#write speedup
	cursor.execute("PRAGMA synchronous = OFF")
	cursor.execute("PRAGMA journal_mode = MEMORY")
	cursor.execute("PRAGMA cache_size = 10000")
	cursor.execute("BEGIN TRANSACTION")

	##parse assembly report
	#specifiy accession column
	if acc.startswith('GCF'):
		accn_col = 6
	else:
		accn_col = 4

	seqs_mapping = {}
	num = 0
	mitochondrion = None
	rows = []

	if os.path.exists(ar_file):
		with open(ar_file) as fh:
			for line in fh:
				if line[0] == '#':
					continue

				if not line.strip():
					continue
				
				cols = line.strip().split('\t')
				
				name = cols[0]
				#genbank or refseq accession number
				accn = cols[accn_col]
				num += 1

				if 'mitochondrion' in cols[3].lower():
					mitochondrion = accn

				seqs_mapping[accn] = num

				if 'chromosome' in cols[3].lower():
					if cols[0].isdigit() and len(cols[0]) <= 2:
						name = 'Chr{}'.format(cols[0])
					
					elif cols[0] in ['X', 'Y', 'W', 'Z']:
						name = 'Chr{}'.format(cols[0])
				
				rows.append((num, name, accn))

	#if assembly report file is empty, get sequence name from fasta file
	if not rows:
		with gzip.open(fa_file, 'rt') as fa:
			for line in fa:
				if line[0] == '>':
					num += 1
					name = line[1:].strip().split()[0]
					seqs_mapping[name] = num
					rows.append((num, name, name))

	#refseq-accn column is empty
	elif '' in seqs_mapping:
		seqname_to_gbaccn = {}
		with open(ar_file) as fh:
			for line in fh:
				if line[0] == '#':
					continue

				if not line.strip():
					continue
				
				cols = line.strip().split('\t')

				seqname_to_gbaccn[cols[0]] = cols[4]

		with gzip.open(fa_file, 'rt') as fa:
			for line in fa:
				if line[0] == '>':
					num += 1
					refacc = line[1:].strip().split()[0]
					seqs_mapping[refacc] = num
					for k,v in seqname_to_gbaccn.items():
						if (k.strip() and k in line) or (v.strip() and v in line):
							name = k.strip() or v.strip()

					rows.append((num, name, refacc))


	cursor.executemany("INSERT INTO sequence VALUES (?,?,?)", rows)
	cursor.executemany("INSERT INTO search(rowid,name,accession) VALUES (?,?,?)", rows)

	##Search for microsatellites and extract flanking sequence
	base_count = 0
	atgc_count = 0
	gc_count = 0
	at_count = 0
	seq_count = 0

	for seqid, seq in kseq.fasta(fa_file):
		if seqid == mitochondrion:
			continue

		seq_count += 1
		base_count += len(seq)
		bases = collections.Counter(seq)
		gc_count += bases['G'] + bases['C']
		atgc_count += bases['G'] + bases['C'] + bases['A'] + bases['T']

		#Search for perfect microsatellites
		ssrs = tandem.search_ssr(seq, [12, 7, 5, 4, 4, 4])

		if not ssrs:
			continue

		def iter_ssr():
			for ssr in ssrs:
				yield (None, seqs_mapping[seqid], ssr[3], ssr[4], ssr[0], motifs.standard(ssr[0]), ssr[1], ssr[2], ssr[5])
		conn.cursor().executemany("INSERT INTO ssr VALUES (?,?,?,?,?,?,?,?,?)", iter_ssr())

		#extract flanking sequence for SSRs
		def iter_flank():
			for row in cursor.execute("SELECT * FROM ssr WHERE sequence_id=?", (seqs_mapping[seqid],)):
				s = row[2] - 100 - 1
				if s < 0:
					s = 0
				left = seq[s:row[2]-1]
				right = seq[row[3]:row[3]+100]

				yield (row[0], left, right)
		conn.cursor().executemany("INSERT INTO ssrmeta VALUES (?,?,?)", iter_flank())

		#search for compound microsatellites
		def iter_cssr():
			cssrs = [ssrs[0]]
			for ssr in ssrs[1:]:
				d = ssr[3] - cssrs[-1][4] - 1
				if d<= 10:
					cssrs.append(ssr)
				else:
					if len(cssrs) > 1:
						yield concatenate_cssr(seqs_mapping[seqid], seq, cssrs)

					cssrs = [ssr]

			if len(cssrs) > 1:
				yield concatenate_cssr(seqs_mapping[seqid], seq, cssrs)
		conn.cursor().executemany("INSERT INTO cssr VALUES (?,?,?,?,?,?,?)", iter_cssr())

		#extract flanking sequence for cSSRs
		def iter_cflank():
			for row in cursor.execute("SELECT * FROM cssr WHERE sequence_id=?", (seqs_mapping[seqid],)):
				s = row[2] - 100 - 1
				if s < 0:
					s = 0
				left = seq[s:row[2]-1]
				right = seq[row[3]:row[3]+100]

				yield (row[0], left, right)
		conn.cursor().executemany("INSERT INTO cssrmeta VALUES (?,?,?)", iter_cflank())

	#if annotation file exists, mapping ssr in gene
	if os.path.exists(gff_file):
		#extract all genes from gff annotation file
		gene_mapping = {}
		def iter_gene():
			gene_count = 0
			for row in gff_parser(gff_file):
				if row.feature == 'REGION':
					continue

				if row.feature != 'GENE':
					if 'PARENT' in row.attrs:
						continue

				gene_count += 1

				gene_mapping[row.attrs.ID] = gene_count
				seqid = seqs_mapping[row.seqid]
				gid = row.attrs.ID

				if 'NAME' in row.attrs:
					gname = row.attrs.NAME
				elif 'PRODUCT' in row.attrs:
					gname = row.attrs.PRODUCT
				else:
					gname = row.attrs.ID

				biotype = row.attrs.get('GENE_BIOTYPE', row.feature)
				dbxref = row.attrs.get('DBXREF', '')
				yield (gene_count, seqid, row.start, row.end, gid, gname, biotype, dbxref)
		conn.cursor().executemany("INSERT INTO gene VALUES (?,?,?,?,?,?,?,?)", iter_gene())

		#do mapping
		interval_forest = {}
		locations = {}
		locid = 0
		prev_chrom = None
		starts = []
		ends = []
		indexes = []

		for feature in get_gff_coordinate(gff_file):
			locid += 1
			locations[locid] = feature[3:]

			if feature[0] != prev_chrom:
				if starts:
					starts = numpy.array(starts, dtype=numpy.long)
					ends = numpy.array(ends, dtype=numpy.long)
					indexes = numpy.array(indexes, dtype=numpy.long)
					interval_forest[prev_chrom] = ncls.NCLS(starts, ends, indexes)
				
				prev_chrom = feature[0]
				starts = []
				ends = []
				indexes = []

			starts.append(feature[1])
			ends.append(feature[2])
			indexes.append(locid)

		if starts:
			starts = numpy.array(starts, dtype=numpy.long)
			ends = numpy.array(ends, dtype=numpy.long)
			indexes = numpy.array(indexes, dtype=numpy.long)
			interval_forest[prev_chrom] = ncls.NCLS(starts, ends, indexes)


		feature_to_id = {'CDS': 1, 'exon': 2, '3UTR': 3, 'intron': 4, '5UTR': 5}
		candidates = ['CDS', 'exon', 'UTR', 'intron']
		seqid_to_name = dict(zip(seqs_mapping.values(), seqs_mapping.keys()))
		#mapping ssr
		mappings = []
		for ssr in cursor.execute("SELECT * FROM ssr"):
			seqname = seqid_to_name[ssr[1]]

			if seqname not in interval_forest:
				continue

			res = set(interval_forest[seqname].find_overlap(ssr[2], ssr[3]))
			if not res:
				continue

			feats = [locations[fid[2]] for fid in res]
			for candidate in candidates:
				for feat, gid in feats:
					if candidate in feat:
						mappings.append((ssr[0], gene_mapping[gid], feature_to_id[feat]))
						break
				else:
					continue
				break
		conn.cursor().executemany("INSERT INTO ssrannot VALUES (?,?,?)", mappings)

		#mapping cssr
		mappings = []
		for ssr in cursor.execute("SELECT * FROM cssr"):
			seqname = seqid_to_name[ssr[1]]

			if seqname not in interval_forest:
				continue

			res = set(interval_forest[seqname].find_overlap(ssr[2], ssr[3]))
			if not res:
				continue

			feats = [locations[fid[2]] for fid in res]
			for candidate in candidates:
				for feat, gid in feats:
					if candidate in feat:
						mappings.append((ssr[0], gene_mapping[gid], feature_to_id[feat]))
						break
				else:
					continue
				break
		conn.cursor().executemany("INSERT INTO cssrannot VALUES (?,?,?)", mappings)

	#statistics
	def set_option(name, val):
		conn.cursor().execute("INSERT INTO summary VALUES (?,?,?)", (None, name, val))

	def get_one(sql):
		cur = conn.cursor()
		for row in cur.execute(sql):
			if row[0] is None:
				return 0
			return row[0]
		return 0

	set_option('genome_size', base_count)
	set_option('valid_size', atgc_count)
	set_option('seq_count', seq_count)
	set_option('ns_count', base_count-atgc_count)
	set_option('gc_content', round(gc_count/atgc_count*100, 2))

	#SSR Statistics
	ssr_count = get_one("SELECT COUNT(*) FROM ssr LIMIT 1")
	set_option('ssr_count', ssr_count)
	ssr_length = get_one("SELECT SUM(length) FROM ssr LIMIT 1")
	set_option('ssr_length', ssr_length)
	ssr_average = round(ssr_length/ssr_count, 2)
	set_option('ssr_average', ssr_average)
	ssr_frequency = round(ssr_count/(atgc_count/1000000), 2)
	set_option('ssr_frequency', ssr_frequency)
	ssr_density = round(ssr_length/(atgc_count/1000000), 2)
	set_option('ssr_density', ssr_density)
	genome_cover= round(ssr_length/atgc_count*100, 2)
	set_option('genome_cover', genome_cover)
	set_option('ssr_perseq', round(ssr_count/seq_count, 2))

	ssr_category = 0
	for row in cursor.execute("SELECT COUNT(DISTINCT standard_motif) FROM ssr"):
		ssr_category = row[0]
	set_option('ssr_category', ssr_category)

	ssr_maxrep = ''
	for row in cursor.execute("SELECT motif, max(repeats) FROM ssr"):
		ssr_maxrep = '{} / {}'.format(row[1], row[0])
	set_option('ssr_maxrep', ssr_maxrep)

	ssr_maxlen = ''
	for row in cursor.execute("SELECT motif, max(length) FROM ssr"):
		ssr_maxlen = '{} / {}'.format(row[1], row[0])
	set_option('ssr_maxlen', ssr_maxlen)

	types = {1: 'Mono', 2: 'Di', 3: 'Tri', 4: 'Tetra', 5: 'Penta', 6: 'Hexa'}
	res = {types[row[0]]: row[1] for row in cursor.execute("SELECT ssr_type, count(*) FROM ssr GROUP BY ssr_type")}
	set_option('ssr_types', json.dumps(res))

	feats = {1: 'CDS', 2: 'exon', 3: '3UTR', 4: 'intron', 5: '5UTR'}
	res = {feats[row[0]]: row[1]  for row in cursor.execute("SELECT location, COUNT(*) FROM ssrannot GROUP BY location")}
	set_option('ssr_location', json.dumps(res))

	res = {row[0]: row[1] for row in cursor.execute("SELECT standard_motif, COUNT(*) FROM ssr GROUP BY standard_motif")}
	set_option('ssr_motif', json.dumps(res))

	res = {}
	for i in range(1, 7):
		res[types[i]] = {row[0]: row[1] for row in cursor.execute("SELECT repeats, COUNT(*) FROM ssr WHERE ssr_type=? GROUP BY repeats", (i,))}
	set_option('ssr_repdis', json.dumps(res))

	res = {}
	for i in range(1, 7):
		res[types[i]] = {row[0]: row[1] for row in cursor.execute("SELECT length, COUNT(*) FROM ssr WHERE ssr_type=? GROUP BY length", (i,))}
	set_option('ssr_lendis', json.dumps(res))

	#Compound microsatellite statistics
	cm_count = get_one("SELECT COUNT(*) FROM cssr LIMIT 1")
	if cm_count > 0:
		set_option('cm_count', cm_count)
		cssr_count = get_one("SELECT SUM(complexity) FROM cssr LIMIT 1")
		set_option('cssr_count', cssr_count)
		cssr_length = get_one("SELECT SUM(length) FROM cssr LIMIT 1")
		set_option('cssr_length', cssr_length)
		cssr_average = round(cssr_length/cm_count, 2)
		set_option('cssr_average', cssr_average)
		cssr_percent = round(cssr_count/ssr_count*100, 2)
		set_option('cssr_percent', cssr_percent)
		cssr_frequency = round(cm_count/(atgc_count/1000000), 2)
		set_option('cssr_frequency', cssr_frequency)
		cssr_density = round(cssr_length/(atgc_count/100000), 2)
		set_option('cssr_density', cssr_density)
		cssr_perseq = round(cm_count/seq_count*100, 2)
		set_option('cssr_perseq', cssr_perseq)
		cssr_maxlen = get_one("SELECT MAX(length) FROM cssr")
		set_option('cssr_maxlen', cssr_maxlen)
		cssr_maxcpl = get_one("SELECT MAX(complexity) FROM cssr")
		set_option('cssr_maxcpl', cssr_maxcpl)
		res = {row[0]: row[1] for row in cursor.execute("SELECT complexity, COUNT(*) FROM cssr GROUP BY complexity")}
		set_option('cssr_cpldis', json.dumps(res))
		res = {row[0]: row[1] for row in cursor.execute("SELECT length, COUNT(*) FROM cssr GROUP BY length")}
		set_option('cssr_lendis', json.dumps(res))

	conn.cursor().executescript(INDEX_SQL)
	conn.commit()
	conn.close()

def worker(event, queue, lock, logfile):
	while 1:
		if event.is_set():
			break

		if queue.empty():
			time.sleep(0.1)
			continue

		acc, info = queue.get()

		try:
			search_for_ssrs(acc, info)
		except Exception as e:
			print(e)
			os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)

		print(acc)

		lock.acquire()
		with open(logfile, 'a') as fh:
			fh.write('{}\n'.format(acc))
		lock.release()

## main process started ##
genome_accession_list_file, progress_log_file, cpu_count = sys.argv[1:]

#breakpoint resume
finished = {}
if os.path.exists(progress_log_file):
	with open(progress_log_file) as fh:
		finished = {line.strip() for line in fh}

genomes = {}
with open(genome_accession_list_file) as fh:
	rows = csv.reader(fh)
	for row in rows:
		#accession of genomes list in column 15
		genomes[row[15]] = row


pool = multiprocessing.Pool(cpu_count)
event = multiprocessing.Event()
queue = multiprocessing.Queue(2)
lock = multiprocessing.Lock()

for i in range(cpu_count):
	pool.apply_async(worker, (event, queue, lock, progress_log_file))

for acc, info in genomes.items():
	if acc in finished:
		continue

	while 1:
		if not queue.full():
			queue.put((acc, info))

		else:
			time.sleep(0.1)

event.set()
pool.close()
pool.join()
