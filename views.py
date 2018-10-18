from django.shortcuts import render

# Create your views here.
def index(request):
	return render(request, 'panmicrosatdb/index.html')

def browse(request):
	return render(request, 'panmicrosatdb/browse.html')
