import os
import csv
import sys
import json
import sqlite3

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

			size = summary.get('genome_size', 0)
			gc = summary.get('gc_content', 0)
			ssr = summary.get('ssr_count', 0)
			sra = summary.get('ssr_frequency', 0)
			srd = summary.get('ssr_density', 0)
			cover = summary.get('genome_cover', 0)
			cm = summary.get('cm_count', 0)
			cra = summary.get('cssr_frequency', 0)
			crd = summary.get('cssr_density', 0)
			percent = summary.get('cssr_percent', 0)

			types = json.loads(summary.get('ssr_types', '{}'))

			record = [row[0], row[1], row[3], row[4], row[5], row[15]]
			record.extend([size, gc, ssr, sra, srd, cover, cm, cra, crd, percent])
			record.extend([
				types.get('Mono', 0),
				types.get('Di', 0),
				types.get('Tri', 0),
				types.get('Tetra', 0),
				types.get('Penta', 0),
				types.get('Hexa', 0)
			])
			print('\t'.join(list(map(str,record))))