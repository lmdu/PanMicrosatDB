import sys
import csv

kingdoms = {}
groups = {}
subgroups = {}

#input files are eukaryote, virus, prokaryote best genome xls file
for infile in sys.argv[1:]:
	with open(infile) as fh:
		reader = csv.reader(fh, delimiter='\t')
		for row in reader:
			k = row[3]
			if k == 'Viroids':
				continue

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
	print("{}\t{}\t{}\t{}".format(id_num, i, 1, 0))

for j in sorted(groups, key=cmp):
	id_num += 1
	parent = kingdoms[groups[j]]
	groups[j] = id_num
	print("{}\t{}\t{}\t{}".format(id_num, j.split(';')[-1], 2, parent))

for k in sorted(subgroups, key=cmp):
	id_num += 1
	parent = groups[subgroups[k]]
	print("{}\t{}\t{}\t{}".format(id_num, k.split(';')[-1], 3, parent))
