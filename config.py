import os

class Config:
	ROOT_DIR = '/home/ming/PSMD'
	DB_DIR = os.path.join(ROOT_DIR, 'dbs')
	FASTA_DIR = os.path.join(ROOT_DIR, 'fastas')
	TASK_FASTA_DIR = os.path.join(ROOT_DIR, 'tasks/fastas')
	TASK_RESULT_DIR = os.path.join(ROOT_DIR, 'tasks/results')
	ARIA2C_RPC = 'http://localhost:6800/jsonrpc'
