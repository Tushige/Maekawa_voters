#global variables

def init():
	global cs_init, next_req, tot_exec_time, ip, port, nodes, sets

	cs_int = None
	next_req = None
	tot_exec_time = None
	ip = "localhost"
	port = 8000
	nodes = [0] * 10
	done_connection = False
	sets = {
		1: [1, 2, 3, 4, 7],
		2: [1, 2, 3, 5, 8],
		3: [1, 2, 3, 6, 9],
		4: [1, 4, 7, 5, 6],
		5: [4, 5, 6, 2, 8],
		6: [4, 5, 6, 3, 9],
		7: [1, 4, 7, 8, 9],
		8: [2, 5, 8, 7, 9],
		9: [3, 6, 9, 7, 8]
	}