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
		self.sending_request = False
		#***
		#0: init
		#1: Request
		#2: Held
		#3: Release
		#***
		self.state = 0
		self.sock = {}
		self.reply = 0
		self.timestamp = 0
		#begin receiving connections from other nodes
		self.start_server()
		self.start_client()
		self.start_algorithm()
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

			self.timestamp+=1
			self.send_msg("hi " + str(self.node_id)+' '+str(self.timestamp), self.sock[x])
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
					self.timestamp = max(self.timestamp+1, int(buf[2]))
					peer_id = int(buf[1])
					self.sock[peer_id] = conn
		
				elif(buf[0] == "REQUEST"):
					#print '[Node %d] received request from %d and I have voted: %r\n'%(self.node_id, int(buf[1]), self.voted)
					self.request_handler(int(buf[1]), int(buf[2]))
				elif(buf[0] == "LEAVING"):
					self.timestamp = max(self.timestamp+1, int(buf[2]))
					self.leave_handler()
				elif(buf[0] == "Ya_GOOD"):
					self.reply +=1
					self.timestamp = max(self.timestamp+1, int(buf[2]))
					print '[Node %d] received %dth reply from %d \n'%(self.node_id, self.reply, int(buf[1]))
					self.node_list[self.reply-1] = int(buf[1])
		conn.close()
		#s_server.close()
	def request_handler(self, req_id, req_stamp):
		#don't process others' request until mine has been sent
		while(self.sending_request == True):
			pass
		if(self.state == 2):
			#queue the message
			print '[Node %d] queueing request from %d Reason: Im in HELD\n'%(self.node_id, req_id)
			self.queue.put(req_id)
			return
		elif(self.voted == True):
			#queue the message
			print '[Node %d] queueing request from %d Reason: I voted already\n'%(self.node_id, req_id)
			self.queue.put(req_id)
			return
		elif(self.state == 1):
			#I want CS, decide if you respond to yourself or the other
			if(self.timestamp < req_stamp):
				#queue the message
				print '[Node %d] queueing request from %d Reason: Im in REQUEST(1) my timesampt is less\n'%(self.node_id, req_id)
				self.queue.put(req_id)
				return
			elif(self.timestamp == req_stamp and self.node_id < req_id):
				#queue the message
				print '[Node %d] queueing request from %d Reason: Im in REQUEST(1) my node_id is less than req_id\n'%(self.node_id, req_id)
				self.queue.put(req_id)
				return
		self.timestamp+=1
		self.send_msg("Ya_GOOD "+str(self.node_id)+' '+str(self.timestamp), self.sock[req_id])
		print '[Node %d] voted for %d\n'%(self.node_id, req_id)
		self.voted = True
		#update timestamp
		self.timestamp = max(req_stamp, self.timestamp)
	def leave_handler(self):
		self.voted = False
		#check if you have un-replied messages
		if(not self.queue.empty()):
			waiting_node = self.queue.get()
			self.send_msg("Ya_GOOD "+str(self.node_id) +' '+str(self.timestamp), self.sock[int(waiting_node)])
			print '[Node %d] voted for %d\n'%(self.node_id, waiting_node)
			self.voted = True

	def send_msg(self, msg, conn):
		#print '[Node %d] sending Hi'%self.node_id
		conn.sendall('Start'+msg+'End')

	def start_algorithm(self):
		algo = threading.Thread(target = self.maekawa, args = ())
		time.sleep(1.0)
		algo.start()
		#print '[Node %d] '%self.node_id +  str(self.sock.keys())

	def maekawa(self):
		print '[Node %d] Imma begin maekawa\n'%self.node_id
		self.entry()

	def entry(self):
		self.sending_request = True
		self.state = 1
		self.timestamp+=1
		for x in range(1, 10):
			if(x in self.my_set):
				self.send_msg("REQUEST " + str(self.node_id) +' '+str(self.timestamp), self.sock[x])
		#update my timestamp
		self.sending_request = False
		
		while(self.reply < 5):
			pass
		self.critical_section()
		self.leave()

	def critical_section(self):
		print '[Node %d] Entering CS: time:%f set members: '%(self.node_id, time.time()) + str(self.node_list) + '\n'
		self.state = 2
		time.sleep(float(self.cs_int))

	def leave(self):
		#update flags
		self.state = 3
		self.reply = 0
		self.voted = False
		print '[Node %d] Leaving CS: time:%f \n'%(self.node_id, time.time())
		self.timestamp+=1
		for x in range(1, 10):
			if(x in self.my_set):
				self.send_msg("LEAVING " + str(self.node_id) +' '+str(self.timestamp), self.sock[x])

		time.sleep(float(self.next_req))
		self.entry()






