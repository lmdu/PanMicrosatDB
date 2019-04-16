import sys
import csv

counts = {}
for infile in sys.argv[1:]:
	with open(infile) as fh:
		reader = csv.reader(fh, delimiter='\t')
		for row in reader:
			k = row[3]
			g = row[4].split(',')[0]
			s = row[5].split(',')[0]

			counts[(k,g,s)] = counts.get((k,g,s), 0) + 1

for k, g, s in counts:
	print("{}\t{}\t{}\t{}".format(k, g, s, counts[(k,g,s)]))
