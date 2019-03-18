import json

def make_ssr_type_plot(data):
	items = [{'name':k, 'y': v} for k, v in data.items()]
	return json.dumps(items)

def make_ssr_motif_plot(data):
	data = sorted(data.items(), key=lambda d: d[1], reverse=True)
	items = [[k, v] for k, v in data[:40]]
	return json.dumps(items)

def make_ssr_repeat_plot(data):
	repeats = sorted({int(r) for m in data for r in data[m]})[:32]
	res = []
	for m in data:
		d = []
		for r in repeats:
			d.append(data[m].get(str(r), 'null'))
		res.append({'name': m, 'data': d})

	return (json.dumps(res), json.dumps(repeats))

def make_ssr_length_plot(data):
	lens = sorted({int(l) for m in data for l in data[m]})[:32]
	res = []
	for m in data:
		d = []
		for l in lens:
			d.append(data[m].get(str(l), 'null'))
		res.append({'name': m, 'data': d})

	return (json.dumps(res), json.dumps(lens))

def make_cssr_complexity_plot(data):
	cps = sorted(int(c) for c in data)[:30]
	res = [[c, data[str(c)]] for c in cps]
	return (json.dumps(res))
	
def make_cssr_length_plot(data):
	lens = sorted(int(l) for l in data)[:30]
	res = [[l, data[str(l)]] for l in lens]
	return (json.dumps(res))

def make_plot(parent, data, option):
	if '{' in data or '[' in data or ',' in data:
		data = json.loads(data)

	if option == 'ssr_types':
		parent[option] = make_ssr_type_plot(data)
	
	elif option == 'ssr_motif':
		parent[option] = make_ssr_motif_plot(data)

	elif option == 'ssr_repdis':
		plot = make_ssr_repeat_plot(data)
		parent[option] = plot[0]
		parent['ssr_replabel'] = plot[1]

	elif option == 'ssr_lendis':
		plot = make_ssr_length_plot(data)
		parent[option] = plot[0]
		parent['ssr_lenlabel'] = plot[1]

	elif option == 'cssr_cpldis':
		parent[option] = make_cssr_complexity_plot(data)

	elif option == 'cssr_lendis':
		parent[option] = make_cssr_length_plot(data)

	else:
		parent[option] = data

