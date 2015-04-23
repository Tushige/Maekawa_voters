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
	#get the command line arguments
	try:
		opts, args = getopt.getopt(argv,'-g:', ["filename"])
	except getopt.GetoptError:
		print 'main.py -i <inputfile>'
		sys.exit(2)

	globals.cs_int = argv[0]
	globals.next_req = argv[1]
	globals.tot_exec_time = argv[2]

	#spawn N=9 nodes
	for x in range(1,10):
		print 'starting node %d'%x
		nood = threading.Thread(target=create_node, args = (x,globals.cs_int, globals.next_req, globals.tot_exec_time,))
		nood.start()
def create_node(node_id, cs_int, next_req, tot_exec_time):
	my_node = Node(node_id, cs_int, next_req, tot_exec_time, globals.sets[node_id])
#execution starts here
if __name__ == "__main__":
	print sys.argv
	main(sys.argv[1:])

