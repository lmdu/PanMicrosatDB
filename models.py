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

	class Meta:
		db_table = 'genome'

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

	class Meta:
		db_table = 'statistics'

class Sequence(models.Model):
	name = models.CharField(max_length=50)
	accession = models.CharField(max_length=50)

	class Meta:
		db_table = 'sequence'

class Search(models.Model):
	rowid = models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)
	accession = models.CharField(max_length=50)

	class Meta:
		db_table = 'search'

class SSR(models.Model):
	SSR_TYPES = (
		(1, 'Mono'),
		(2, 'Di'),
		(3, 'Tri'),
		(4, 'Tetra'),
		(5, 'Penta'),
		(6, 'Hexa')
	)
	sequence = models.ForeignKey(Sequence, on_delete=models.CASCADE)
	start = models.IntegerField()
	end = models.IntegerField()
	motif = models.CharField(max_length=6)
	standard_motif = models.CharField(max_length=6)
	ssr_type = models.SmallIntegerField(choices=SSR_TYPES)
	repeats = models.IntegerField()
	length = models.IntegerField()

	class Meta:
		db_table = 'ssr'

class SSRMeta(models.Model):
	ssr = models.OneToOneField(SSR, on_delete=models.CASCADE)
	left_flank = models.CharField(max_length=100)
	right_flank = models.CharField(max_length=100)

	class Meta:
		db_table = 'ssrmeta'

class SSRAnnot(models.Model):
	FEAT_TYPES = (
		(1, 'CDS'),
		(2, 'exon'),
		(3, '3UTR'),
		(4, 'intron'),
		(5, '5UTR')
	)
	ssr = models.ForeignKey(SSR, on_delete=models.CASCADE)
	gene_id = models.CharField(max_length=20)
	gene_name = models.CharField(max_length=20)
	location = models.SmallIntegerField(choices=FEAT_TYPES)

	class Meta:
		db_table = 'ssrannot'

class CSSR(models.Model):
	sequence = models.ForeignKey(Sequence, on_delete=models.CASCADE)
	start = models.IntegerField()
	end = models.IntegerField()
	complexity = models.IntegerField()
	length = models.IntegerField()
	structure = models.CharField(max_length=255)

	class Meta:
		db_table = 'cssr'

class CSSRMeta(models.Model):
	cssr = models.OneToOneField(CSSR, on_delete=models.CASCADE)
	left_flank = models.CharField(max_length=100)
	right_flank = models.CharField(max_length=100)
	
	class Meta:
		db_table = 'cssrmeta'

class CSSRAnnot(models.Model):
	FEAT_TYPES = (
		(1, 'CDS'),
		(2, 'exon'),
		(3, '3UTR'),
		(4, 'intron'),
		(5, '5UTR')
	)
	cssr = models.ForeignKey(CSSR, on_delete=models.CASCADE)
	gene_id = models.CharField(max_length=20)
	gene_name = models.CharField(max_length=20)
	location = models.SmallIntegerField(choices=FEAT_TYPES)

	class Meta:
		db_table = 'cssrannot'

class SSRStat(models.Model):
	name = models.CharField(max_length=30)
	val = models.FloatField()

	class Meta:
		db_table = 'ssrstat'

