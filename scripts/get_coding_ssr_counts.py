import os
import csv
import sys
import sqlite3

WORK_DIR = '/home/ming/PSMD'
DB_DIR = os.path.join(WORK_DIR, 'dbs')


for infile in sys.argv[1:]:
	with open(infile) as fh:
		rows = csv.reader(fh, delimiter='\t')
		for row in rows:
			if row[3] == 'Viroids':
				continue

			if ',' in row[4]:
				row[4] = row[4].split(',')[0]

			sub_dir = os.path.join(*row[3:6]).replace(' ', '_')
			db_file = os.path.join(DB_DIR, sub_dir, '{}.db'.format(row[15]))

			conn = sqlite3.connect(db_file)
			cursor = conn.cursor()
			
			for record in cursor.execute("SELECT COUNT(*) FROM ssr"):
				total_ssr = record[0]

			if total_ssr == 0:
				continue

			for record in cursor.execute("SELECT COUNT(*) FROM ssrannot"):
				genic_ssr = record[0]

			for record in cursor.execute("SELECT COUNT(*) FROM ssrannot WHERE location=1"):
				cds_ssr = record[0]

			for record in cursor.execute("SELECT COUNT(*) FROM cssr"):
				total_cssr = record[0]

			for record in cursor.execute("SELECT COUNT(*) FROM cssrannot"):
				genic_cssr = record[0]

			for record in cursor.execute("SELECT COUNT(*) FROM cssrannot WHERE location=1"):
				cds_cssr = record[0]

			for record in cursor.execute("SELECT SUM(complexity) FROM cssr"):
				complexity = record[0]

			cursor.close()
			conn.close()

			if genic_ssr == 0:
				continue

			res = [row[0], row[1], row[3], row[4], row[5]]
			res.extend([total_ssr, genic_ssr, cds_ssr, total_ssr-cds_ssr, total_cssr, genic_cssr, cds_cssr, total_cssr-cds_cssr, complexity])

			print("\t".join(list(map(str,res))))
