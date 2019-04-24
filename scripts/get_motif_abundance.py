import os
import csv
import sys
import json
import sqlite3

from ..thirds.motifs import *

motifs = MotifStandard(2).get_motifs()

headers = ["kingdom", "group", "subgroup"]
headers.extend(motifs)
print("\t".join(headers))

WORK_DIR = '/home/ming/PSMD'
DB_DIR = os.path.join(WORK_DIR, 'dbs')

for infile in sys.argv[1:]:
	with open(infile) as fh:
		rows = csv.reader(fh, delimiter='\t')
		for row in rows:
			if ',' in row[4]:
				row[4] = row[4].split(',')[0]

			sub_dir = os.path.join(*row[3:6]).replace(' ', '_')
			db_file = os.path.join(DB_DIR, sub_dir, '{}.db'.format(row[15]))

			conn = sqlite3.connect(db_file)
			cursor = conn.cursor()
			summary = {r[1]:r[2] for r in cursor.execute("SELECT * FROM summary")}
			cursor.close()
			conn.close()

			genome_size = int(summary['valid_size'])/1000000

			motif_counts = json.loads(summary['ssr_motif'])

			res = row[3:6]

			for motif in motifs:
				if motif in motif_counts:
					rd = int(motif_counts[motif])*len(motif)/genome_size
				else:
					rd = 0
				res.append(str(rd))

			print("\t".join(res))

