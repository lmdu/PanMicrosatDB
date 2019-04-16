import os
import csv
import sys
import sqlite3

WORK_DIR = '/home/ming/PSMD'
DB_DIR = os.path.join(WORK_DIR, 'dbs')
total_coding_ssrs = 0
total_coding_cssrs = 0
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
			for row in cursor.execute("SELECT COUNT(*) FROM ssrannot WHERE location=1"):
				total_coding_ssrs += row[0]
				
			for row in cursor.execute("SELECT COUNT(*) FROM cssrannot WHERE location=1"):
				total_coding_cssrs += row[0]

			cursor.close()
			conn.close()

print(total_coding_ssrs)
print(total_coding_cssrs)
