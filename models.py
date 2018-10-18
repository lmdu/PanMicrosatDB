from django.db import models

# Create your models here.
class Genome(models.Model):
	taxonomy = models.CharField(max_length=20)
	species_name = models.CharField(max_length=255)
	common_name = models.CharField(max_length=255)
	kingdom = models.CharField(max_length=20)
	groups = models.CharField(max_length=30)
	subgroup = models.CharField(max_length=50)
	biosample = models.CharField(max_length=15)
	bioproject = models.CharField(max_length=15)
	assembly_level = models.CharField(max_length=15)
	assembly_accession = models.CharField(max_length=20, help_text='assembly accession in genbank')
	download_accession = models.CharField(max_length=20, help_text='accession of used sequence file')
	size = models.BigIntegerField()
	gc_content = models.FloatField()
	ns_count = models.IntegerField()
	seq_count = models.IntegerField(help_text='number of sequences in fasta')
	gene_count = models.IntegerField(help_text='number of genes')
	download_link = models.CharField(max_length=255)

class Statistics(models.Model):
	genome = models.OneToOneField(Genome, on_delete=models.CASCADE)
	ssr_count = models.IntegerField()
	mono_count = models.IntegerField()
	di_count = models.IntegerField()
	tri_count = models.IntegerField()
	tetra_count = models.IntegerField()
	penta_count = models.IntegerField()
	hexa_count = models.IntegerField()
	ssr_frequency = models.FloatField()
	ssr_density = models.FloatField()
	cover = models.FloatField()
	cm_count = models.IntegerField()
	cssr_count = models.IntegerField()
	cssr_percent = models.FloatField()
	cssr_frequency = models.FloatField()
	cssr_density = models.FloatField()

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
	start = models.IntegerField()
	end = models.IntegerField()
	motif = models.CharField(max_length=6)
	standard_motif = models.CharField(max_length=6)
	ssr_type = models.SmallIntegerField(choices=SSR_TYPES)
	repeats = models.IntegerField()
	length = models.IntegerField()

class SSRMeta(models.Model):
	ssr = models.OneToOneField(SSR, on_delete=models.CASCADE)
	left_flank = models.CharField(max_length=100)
	right_flank = models.CharField(max_length=100)

class SSRAnnot(models.Model):
	ssr = models.ForeignKey(SSR, on_delete=models.CASCADE)
	gene = models.CharField(max_length=20)
	location = models.SmallIntegerField()

class CSSR(models.Model):
	chrom = models.CharField(max_length=50)
	start = models.IntegerField()
	end = models.IntegerField()
	motif = models.CharField(max_length=255)
	complexity = models.SmallIntegerField()
	length = models.IntegerField()
	gap = models.IntegerField()

class CSSRMeta(models.Model):
	cssr = models.OneToOneField(CSSR, on_delete=models.CASCADE)
	structure = models.CharField(max_length=255)
	self_seq = models.CharField(max_length=255)
	left_flank = models.CharField(max_length=100)
	right_flank = models.CharField(max_length=100)

class CSSRAnnot(models.Model):
	cssr = models.ForeignKey(CSSR, on_delete=models.CASCADE)
	gene = models.CharField(max_length=20)
	location = models.SmallIntegerField()

