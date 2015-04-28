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

node_obj = [None] * 15

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
	#user_input()

	#spawn N=9 nodes
	for x in range(1,10):
		nood = threading.Thread(target=create_node, args = (x,globals.cs_int, globals.next_req, globals.tot_exec_time,))
		nood.start()

def create_node(node_id, cs_int, next_req, tot_exec_time):
	global node_obj
	my_node = Node(node_id, cs_int, next_req, tot_exec_time, globals.sets[node_id])
	node_obj[node_id] = my_node
#def user_input():
	#cmda = threading.Thread(target = gimme, args = ())
	#cmda.start()

#def gimme():
#	global node_obj
#	while(1):
#		if globals.end:
#			break
#		userInput = raw_input('>>> ')
#		cmd = userInput.split(' ')
#		if cmd[0] == "show" :
#			for x in range(1, 10):
#				node_obj[x].show()
#	print 'OUT\n'
#	sys.exit()

#execution starts here
if __name__ == "__main__":
	print sys.argv
	main(sys.argv[1:])

