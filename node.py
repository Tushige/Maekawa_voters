#Nodes
import socket
import sys, getopt
import threading
import thread
import time
import datetime
import random
from collections import deque
#my imports
import globals

class Node:
	def __init__(self, node_id, cs_int, next_req, tot_exec_time):
		self.node_id = node_id
		# times 
		self.cs_int = cs_int
		self.next_req = next_req
		self.tot_exec_time = tot_exec_time
		#***
		#0: init
		#1: Request
		#2: Held
		#3: Release
		#***
		self.state = 0
		self.sock = {}

		#begin receiving connections from other nodes
		self.start_server()
		self.start_client()
	def start_server(self):
		my_server = threading.Thread(target = self.serverThread, args = ())
		my_server.start()
	def start_client(self):
		#connect to N=9 other nodes
		for x in range (1, 10):
			if x is self.node_id or self.sock.has_key(x):
				#don't connect to yourself
				continue
			peer_port = globals.port + x
			while(globals.nodes[x] == 0):
				pass
			try:
				self.sock[x] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			except socket.error, msg:
				print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1] + '\n'
				sys.exit();

			self.sock[x].connect((globals.ip, peer_port))
			#print '[Node %d] Connected to Node_%d\n' %(self.node_id, x)

			self.send_msg("hi " + str(self.node_id), self.sock[x])
			#start a listening thread
			recv_t = threading.Thread(target= self.recvThread, args = (self.sock[x],))
			recv_t.start()

	def serverThread(self):
		s_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		try: #setup server socket
			s_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			node_port = globals.port + self.node_id
			s_server.bind((globals.ip, node_port))

			#indicate that your listening now, so other nodes can connect to you
			globals.nodes[self.node_id] = 1
		except socket.error, msg:
			print '[[ Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1] + ' ]]'
			sys.exit()
		s_server.listen(10)
		while(1):
			conn, addr = s_server.accept()
			#check if connection already exists
			list_socks = self.sock.values()
			if conn in list_socks:
				conn.close()
				continue
			#print '[Node %d] connected to '%self.node_id + str(addr[1]) + '\n'
			r_thread = threading.Thread(target = self.recvThread, args = (conn,))
			r_thread.start()
	def recvThread(self, conn):
		while(1):
			total_data=[]
			end_idx = 0
			data = conn.recv(1024)
			length = len(data)
			while end_idx < length:
				if "Start" in data:
					start_idx = data.find("Start")
					end_idx = data.find("End")
					total_data.append(data[start_idx+5:end_idx])
					temp = data[end_idx+3:len(data)]
					data = temp
				else:
					break
				if len(total_data) > 1:
					last_pair = total_data[-2] + total_data[-1]
					if "End" in last_pair:
						total_data[-2]=last_pair[:last_pair.find('End')]
						total_data.pop()
						break
			for j in range(0,len(total_data)):
				single_msg = ''.join(total_data[j])
				buf = single_msg.split(' ')

				if(buf[0] == "hi"):
					peer_id = int(buf[1])
					print '[Node %d] Received connection from '%self.node_id + str(peer_id) + '\n'
					self.sock[peer_id] = conn

		#def threadShouldStop():
			#returns true when tot_exec_time expires
		conn.close()
		s_server.close()

	def send_msg(self, msg, conn):
		#print '[Node %d] sending Hi'%self.node_id
		conn.sendall('Start'+msg+'End')






