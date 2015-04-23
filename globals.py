#global variables

def init():
	global cs_init, next_req, tot_exec_time, ip, port, nodes

	cs_int = None
	next_req = None
	tot_exec_time = None
	ip = "localhost"
	port = 8000
	nodes = [0] * 10