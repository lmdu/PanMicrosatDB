import os

class Config:
	ROOT_DIR = '/mnt/d/research/PSMD/'
	DB_DIR = os.path.join(ROOT_DIR, 'dbs')
	TASK_FASTA_DIR = os.path.join(ROOT_DIR, 'tasks/fastas')
	TASK_RESULT_DIR = os.path.join(ROOT_DIR, 'tasks/results')
	ARIA2C_RPC = 'http://localhost:6800/jsonrpc'
