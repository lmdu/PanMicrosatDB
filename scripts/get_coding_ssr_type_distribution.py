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

			cursor.execute("SELECT COUNT(*) FROM ssrannot")
			if not cursor.fetchone()[0]:
				continue
			
			counts = {}
			for record in cursor.execute("SELECT ssr.ssr_type, COUNT(*) FROM ssr,ssrannot WHERE ssr.id=ssrannot.ssr_id AND ssrannot.location=1 GROUP BY ssr.ssr_type"):
				counts[record[0]] = record[1]

			cursor.close()
			conn.close()

			res = [row[0], row[1], row[3], row[4], row[5]]
			res.extend([counts.get(i, 0) for i in range(1,7)])

			print("\t".join(list(map(str,res))))
