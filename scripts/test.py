import os
import time
import signal
import multiprocessing as mp

def init_worker():
	signal.signal(signal.SIGINT, signal.SIG_IGN)

def woker(x):
	time.sleep(x)
	print(mp.current_process().name)
	try:
		raise Exception('error orccured')
	except Exception as e:
		print(e)
		os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)


pool = mp.Pool(3, init_worker)

for i in range(10,20):
	pool.apply_async(woker, (i,))
pool.close()
pool.join()

