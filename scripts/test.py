import multiprocessing as mp
import time

def testme(q, e):
	name = mp.current_process().name
	while 1:
		if e.is_set() and q.empty():
			break

		if q.empty():
			time.sleep(0.1)
			continue

		x, y = q.get_nowait()
		print('{} get {} * {}'.format(name, x, ''.join(y)))
		time.sleep(x)

	print('{} stopped'.format(name))
	return

if __name__ == '__main__':
	m = mp.Manager()
	pool = mp.Pool(2)
	q = m.Queue(2)
	e = m.Event()

	for i in range(2):
		pool.apply_async(testme, (q,e))

	for i in range(10):
		q.put((i,[str(i),str(i)]))

	e.set()
	pool.close()
	pool.join()
