from django.db import models

# Create your models here.
class Genome(models.Model):
	taxonomy = models.IntegerField()
	species_name = models.CharField(max_length=255)
	common_name = models.CharField(max_length=255)
	kingdom = models.CharField(max_length=20)
	groups = models.CharField(max_length=30)
	subgroup = models.CharField(max_length=50)
	biosample = models.CharField(max_length=15)
	bioproject = models.CharField(max_length=15)
	assembly_level = models.CharField(max_length=15)
	assembly_accession = models.CharField(max_length=20, help='assembly accession in genbank')
	download_accession = models.CharField(max_length=20, help='accession of used sequence file')
	size = models.BigIntegerField()
	gc_content = models.FloatField()
	seq_count = models.IntegerField(help='number of sequences in fasta')
	gene_count = models.IntegerField(help='number of genes')
	download_link = models.models.CharField(max_length)

class SSR(models.Model):
	SSR_TYPES = (
		(1, 'Mono'),
		(2, 'Di'),
		(3, 'Tri'),
		(4, 'Tetra'),
		(5, 'Penta'),
		(6, 'Hexa')
	)
	chrom = models.CharField(max_length=50)
	start = IntegerField()
	end = IntegerField()
	motif = models.CharField(max_length=6)
	standard_motif = models.CharField(max_length=6)
	ssr_type = models.SmallIntegerField(choices=SSR_TYPES)
	repeats = models.IntegerField()
	length = IntegerField()

class SSRMeta(models.Model):
	ssr = OneToOneField(SSR, on_delete=models.CASCADE)
	left_flank = models.CharField(max_length=100)
	right_flank = models.CharField(max_length=100)

class CSSR(models.Model):
	chrom = models.CharField(max_length=50)
	start = IntegerField()
	end = IntegerField()
	motif = models.CharField(max_length=255)
	complexity = models.SmallIntegerField()
	length = IntegerField()
	gap = IntegerField()

class CSSRMeta(models.Model):
	cssr = OneToOneField(CSSR, on_delete=models.CASCADE)
	structure = models.CharField(max_length=255)
	self_seq = models.CharField(max_length=255)
	left_flank = models.CharField(max_length=100)
	right_flank = models.CharField(max_length=100)


