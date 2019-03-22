from django.urls import path

from . import views

urlpatterns = [
	path('', views.index, name='index'),
	path('category', views.category, name='category'),
	path('overview', views.overview, name='overview'),
	path('species', views.species, name='species'),
	path('browse', views.browse, name='browse'),
	path('compound', views.compound, name='cssrs'),
	path('download', views.download, name='download'),
	path('seqid', views.sequence, name='seqid'),
	path('flank', views.flank, name='flank'),
	path('cssrdetail', views.get_cssr_detail, name='cssr_detail'),
	path('krait', views.krait, name='krait'),
	path('task/<task_id>', views.task, name='task'),
]