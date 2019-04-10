import os
import csv
import sys
import sqlite3

WORK_DIR = '/home/ming/PSMD'
DB_DIR = os.path.join(WORK_DIR, 'dbs')

kingdoms = {}
groups = {}
subgroups = {}

#input files are eukaryote, virus, prokaryote best genome xls file
for infile in sys.argv[1:]:
	with open(infile) as fh:
		reader = csv.reader(fh, delimiter='\t')
		for row in reader:
			k = row[3]
			g = row[4].split(',')[0]
			s = row[5].split(',')[0]

			kingdoms[k] = 0
			groups[";".join([k, g])] = k
			subgroups[";".join([k, g, s])] = ";".join([k, g])

def cmp(x):
	x = x.split(';')[-1]
	if x.startswith('unclassified'):
		if x == 'unclassified':
			return 'zzzzz'
		else:
			return 'zzzzz {}'.format(x.split()[1])

	elif x.startswith('Other'):
		if x == 'Other':
			return 'zzzzzzzz'
		else:
			return 'zzzzzzzz {}'.format(x.split()[1])
	else:
		return x

id_num = 0
for i in sorted(kingdoms):
	id_num += 1
	kingdoms[i] = id_num

for j in sorted(groups, key=cmp):
	id_num += 1
	groups[j] = id_num

for k in sorted(subgroups, key=cmp):
	id_num += 1
	subgroups[k] = id_num


species_num = 0
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

			k = row[3]
			g = row[4].split(',')[0]
			s = row[5].split(',')[0]

			species_num += 1
			record = [species_num, row[0], row[1], row[2], row[6], row[7], row[9].strip(), row[8], row[15], row[14]]
			record.extend([size, gc, ssr, sra, srd, cover, cm, cra, crd, percent])
			record.append(subgroups[";".join([k, g, s])])
			print('\t'.join(list(map(str,record))))

