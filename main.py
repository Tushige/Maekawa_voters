#main.py

import socket
import sys, getopt
import threading
import thread
import time
import datetime
import random
from collections import deque

#my imports
from node import Node
import globals

def main(argv):
	#initialize the global variables
	globals.init()
	sys.setrecursionlimit(10000)
	#get the command line arguments
	try:
		opts, args = getopt.getopt(argv,'-g:', ["filename"])
	except getopt.GetoptError:
		print 'main.py -i <inputfile>'
		sys.exit(2)

	if argv[0] < 0 or argv[1] < 0 or argv[2] < 0:
		print '[invalid input]'
		sys.exit(2)

	globals.cs_int = int(argv[0])
	globals.next_req = int(argv[1])
	globals.tot_exec_time = int(argv[2])

	#spawn N=9 nodes
	for x in range(1,10):
		nood = threading.Thread(target=create_node, args = (x,globals.cs_int, globals.next_req, globals.tot_exec_time,int(argv[3])))
		nood.start()
	while(not globals.end):
		pass
	del globals.node_obj

def create_node(node_id, cs_int, next_req, tot_exec_time, option):
	my_node = Node(node_id, cs_int, next_req, tot_exec_time, globals.sets[node_id],option)
	globals.node_obj[node_id] = my_node

#execution starts here
if __name__ == "__main__":
	print sys.argv
	main(sys.argv[1:])

