#Nodes
import socket
import sys, getopt
import threading
import thread
import time
import datetime
import random
import Queue
import datetime
#my imports
import globals

class Node:
	def __init__(self, node_id, cs_int, next_req, tot_exec_time, set):
		self.node_id = node_id
		# times 
		self.cs_int = cs_int
		self.next_req = next_req
		self.tot_exec_time = tot_exec_time
		self.voted = False
		self.my_set = set
		self.node_list = [None]*5
		self.queue = Queue.Queue()
		#***
		#0: init
		#1: Request
		#2: Held
		#3: Release
		#***
		self.state = 0
		self.sock = {}
		self.count = 0
		self.reply = 0
		#begin receiving connections from other nodes
		self.start_server()
		self.start_client()
		self.start_algorithm()
		#print '[Node %d] '%self.node_id +  str(self.sock.keys())
	def start_server(self):
		my_server = threading.Thread(target = self.serverThread, args = ())
		my_server.start()
	def start_client(self):
		#connect to N=9 other nodes
		for x in range (self.node_id, 10):
			peer_port = globals.port + x
			while(globals.nodes[x] == 0):
				pass
			try:
				self.sock[x] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			except socket.error, msg:
				print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1] + '\n'
				sys.exit();

			self.sock[x].connect((globals.ip, peer_port))

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
			r_thread = threading.Thread(target = self.recvThread, args = (conn,))
			r_thread.start()
	def recvThread(self, conn):
		end = 0
		while(not end):
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
					#print '[Node %d] Received connection from '%self.node_id + str(peer_id) + '\n'
					self.sock[peer_id] = conn
					self.count+=1
					if(self.count == self.node_id - 1):
						print '[Node %d] '%self.node_id +  str(self.sock.keys())
		
				elif(buf[0] == "REQUEST"):
					if(self.state == 2 or self.voted == True):
						#queue the message
						self.queue.put(buf[1])
					else:
						self.send_msg("Ya_GOOD "+str(self.node_id), conn)
						self.voted = True
				elif(buf[0] == "LEAVING"):
					self.voted = False
				elif(buf[0] == "Ya_GOOD"):
					self.reply +=1
					print '[Node %d] received %dth reply from %d \n'%(self.node_id, self.reply, int(buf[1]))
					self.node_list[self.reply-1] = int(buf[1])
		conn.close()
		#s_server.close()

	def send_msg(self, msg, conn):
		#print '[Node %d] sending Hi'%self.node_id
		conn.sendall('Start'+msg+'End')

	def start_algorithm(self):
		algo = threading.Thread(target = self.maekawa, args = ())
		algo.start()
	def maekawa(self):
		#delay to allow the network to be setup
		time.sleep(1.0)
		print '[Node %d] Imma begin maekawa\n'%self.node_id
		self.entry()
	def entry(self):
		self.state = 1
		for x in range(1, 10):
			if(x in self.my_set):
				self.send_msg("REQUEST " + str(self.node_id), self.sock[x])
		while(self.reply < 5):
			pass
		self.critical_section()
		self.leave()
	def critical_section(self):
		#print '%f %d '%(time.time(), self.node_id) + str(self.node_list) + '\n'
		print '[Node %d] Entering CS: time:%f set members: '%(self.node_id, time.time()) + str(self.node_list) + '\n'
		self.state = 2
		time.sleep(float(self.cs_int))
	def leave(self):
		#update flags
		self.state = 3
		self.reply = 0
		print '[Node %d] Leaving CS: time:%f \n'%(self.node_id, time.time())
		for x in range(1, 10):
			if(x in self.my_set):
				self.send_msg("LEAVING " + str(self.node_id), self.sock[x])
		#check if you have un-replied messages
		if(not self.queue.empty()):
			waiting_node = self.queue.get()
			self.send_msg("Ya_GOOD "+str(self.node_id), self.sock[int(waiting_node)])
			self.voted = True
		else:
			self.voted = False

		time.sleep(float(self.next_req))
		self.entry()






