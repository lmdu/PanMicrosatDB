from django.contrib import admin
from .models import *
# Register your models here.

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
	list_display = ('job_id', 'mode', 'status', 'created')

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
	list_display = ('title', 'abstract', 'content', 'created')
