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
			if ',' in row[4]:
				row[4] = row[4].split(',')[0]

			sub_dir = os.path.join(*row[3:6]).replace(' ', '_')
			db_file = os.path.join(DB_DIR, sub_dir, '{}.db'.format(row[15]))

			conn = sqlite3.connect(db_file)
			cursor = conn.cursor()
			
			for row in cursor.execute("SELECT COUNT(*) FROM ssr"):
				total_ssr = row[0]

			for row in cursor.execute("SELECT COUNT(*) FROM ssrannot"):
				genic_ssr = row[0]

			for row in cursor.execute("SELECT COUNT(*) FROM ssrannot WHERE location=1"):
				cds_ssr = row[0]

			for row in cursor.execute("SELECT COUNT(*) FROM cssr"):
				total_cssr = row[0]

			for row in cursor.execute("SELECT COUNT(*) FROM cssrannot"):
				genic_cssr = row[0]

			for row in cursor.execute("SELECT COUNT(*) FROM cssrannot WHERE location=1"):
				cds_cssr = row[0]

			cursor.close()
			conn.close()

			if genic_ssr == 0:
				continue

			res = list(row[3:6])
			res.extend([genic_ssr, cds_ssr, total_ssr-cds_ssr, genic_cssr, cds_cssr, total_cssr-cds_cssr])

			print("\t".join(list(map(str,res))))
