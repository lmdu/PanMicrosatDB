from django.db import models

# Create your models here.
class Category(models.Model):
	LEVLES = (
		(1, 'Kingdom'),
		(2, 'Group'),
		(3, 'Subgroup')
	)
	name = models.CharField(max_length=50)
	level = models.SmallIntegerField(choices=LEVLES)
	parent = models.ForeignKey('self', on_delete=models.CASCADE)

	
	class Meta:
		db_table = 'category'

class Genome(models.Model):
	taxonomy = models.CharField(max_length=20)
	species_name = models.CharField(max_length=255)
	common_name = models.CharField(max_length=255)
	biosample = models.CharField(max_length=15)
	bioproject = models.CharField(max_length=15)
	assembly_level = models.CharField(max_length=15)
	assembly_accession = models.CharField(max_length=20, help_text='assembly accession in genbank')
	download_accession = models.CharField(max_length=20, help_text='accession of used sequence file')
	gene_count = models.IntegerField()
	size = models.BigIntegerField()
	gc_content = models.FloatField()
	ssr_count = models.IntegerField()
	ssr_frequency = models.FloatField()
	ssr_density = models.FloatField()
	cover = models.FloatField()
	cm_count = models.IntegerField()
	cm_frequency = models.FloatField()
	cm_density = models.FloatField()
	cssr_percent = models.FloatField()
	category = models.ForeignKey(Category, on_delete=models.CASCADE)

	class Meta:
		db_table = 'genome'

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

class Gene(models.Model):
	sequence = models.ForeignKey(Sequence, on_delete=models.CASCADE)
	start = models.IntegerField()
	end = models.IntegerField()
	gid = models.CharField(max_length=30)
	name = models.CharField(max_length=30)
	biotype = models.CharField(max_length=20)
	dbxref = models.CharField(max_length=200)

	class Meta:
		db_table = 'gene'

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
	ssr = models.OneToOneField(SSR, on_delete=models.CASCADE, primary_key=True)
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
	ssr = models.OneToOneField(SSR, on_delete=models.CASCADE, primary_key=True)
	gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
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
	cssr = models.OneToOneField(CSSR, on_delete=models.CASCADE, primary_key=True)
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
	cssr = models.OneToOneField(CSSR, on_delete=models.CASCADE, primary_key=True)
	gene_id = models.ForeignKey(Gene, on_delete=models.CASCADE)
	location = models.SmallIntegerField(choices=FEAT_TYPES)

	class Meta:
		db_table = 'cssrannot'

class Summary(models.Model):
	option = models.CharField(max_length=30)
	content = models.FloatField()

	class Meta:
		db_table = 'summary'

