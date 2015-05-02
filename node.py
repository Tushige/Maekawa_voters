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
	def __init__(self, node_id, cs_int, next_req, tot_exec_time, set, option):
		#*****
		# node instance variables
		#*****
		self.node_id = node_id
		self.cs_int = cs_int
		self.next_req = next_req
		self.tot_exec_time = tot_exec_time
		self.option = option

		self.voted = False
		self.my_set = set
		self.pending = Queue.PriorityQueue()
		self.msg_queue = Queue.Queue(-10)
		self.sending_request = False
		self.lock = threading.Lock()
		self.sendlock = threading.Lock()
		self.state = 0 #0: init, 1: Request, 2: Held, 3: Release
		self.sock = {}
		self.reply = 0
		self.my_choice = {}
		self.send_stamp = 0
		self.timestamp = 0
		self.failed_count = 0
		self.granters = [""] * 5
		self.granted = ''
		self.end = 0
		self.waited = 0
		#*****
		#Begin Node setup
		#*****
		try:
			globals.node_obj[self.node_id] = self
		except:
			print self.node_id
		self.setup()

	def setup(self):
		msg = threading.Thread(target = self.send_msg, args = ())
		msg.setDaemon(True)
		msg.start()
		self.start_server()
		self.start_client()
		self.maekawa()

	def start_server(self):
		my_server = threading.Thread(target = self.serverThread, args = ())
		my_server.setDaemon(True)
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
				#print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1] + '\n'
				sys.exit();
			self.sock[x].connect((globals.ip, peer_port))

			#self.timestamp+=1
			self.msg_queue.put( ("hi " + str(self.node_id)+' '+str(self.timestamp), self.sock[x]) )
			#self.send_msg("hi " + str(self.node_id)+' '+str(self.timestamp), self.sock[x])
			#start a listening thread
			recv_t = threading.Thread(target= self.recvThread, args = (self.sock[x],))
			recv_t.setDaemon(True)
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
			#print '[[ Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1] + ' ]]'
			sys.exit()
		s_server.listen(10)
		while(not self.end):
			conn, addr = s_server.accept()
			r_thread = threading.Thread(target = self.recvThread, args = (conn,))
			r_thread.setDaemon(True)
			r_thread.start()
		s_server.close()

	def recvThread(self, conn):
		while(not self.end):
			try:
				data = conn.recv(1024)
			except:
				continue
			if len(data) == 0:
				continue
			while data[-1] != '\n' and self.end==0:
				data = data + conn.recv(1024)
			messages = data.split('\n')
			for ss in messages:
				buf = ss.split(' ')
				if(buf[0] == ''):
					continue
				if self.option == 1:
					print '[%f] [Node %d] [From:%d] [type:%s] [timestamp: %s]\n'%(time.time(), self.node_id, int(buf[1]), buf[0], buf[2])
				if(buf[0] == "hi"):
					peer_id = int(buf[1])
					self.sock[peer_id] = conn
		
				elif(buf[0] == "REQUEST"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.lock.acquire()
					self.request_handler(int(buf[1]), int(buf[2]))
					self.lock.release()

				elif(buf[0] == "LEAVING"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.leave_handler(int(buf[1]))
					#self.failed_count = 0

				elif(buf[0] == "grant"):
					try:
						self.granters[self.reply] = int(buf[1])
					except:
						print '[Node %d]***OUT OF RANGE***from %d %dth reply****\n'%(self.node_id, int(buf[1]), self.reply,)
					self.reply +=1
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)		

				elif(buf[0] == "grant_yielded"):
					self.granters[self.reply] = int(buf[1])
					self.reply +=1
					self.failed_count -=1
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)

				elif(buf[0] == "inquire"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.inquire_handler(int(buf[1]), int(buf[3]), int(buf[4]))

				elif(buf[0] == "yield"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.yield_handler(int(buf[1]), int(buf[2]))

				elif(buf[0] == "failed"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.failed_count+=1
					#print '[Node %d] received Failed from %d\n'%(self.node_id, int(buf[1]))
		conn.close()

	def request_handler(self, req_id, req_stamp):
		#don't process others' request until mine has been sent
		while(self.sending_request == True):
			pass
		choose_myself = (self.state == 1 and (self.send_stamp < req_stamp or (self.send_stamp==req_stamp and self.node_id < req_id)))
		if(self.state == 2 or self.voted == True or choose_myself):
			self.pending.put((req_stamp, req_id)) # queue the message
			self.timestamp+=1
			self.msg_queue.put( ('failed ' +str(self.node_id) + ' ' + str(self.timestamp), self.sock[req_id]) )
			#check if the requester has higher priority than my current choice
			if(self.voted == True):
				if(req_stamp < self.my_choice['timestamp'] or (req_stamp == self.my_choice['timestamp'] and req_id < self.my_choice['id'])):
					#if new request has higher priority than my accepted request
					self.timestamp+=1
					self.msg_queue.put( ("inquire " + str(self.node_id) +' ' + str(self.timestamp) + ' ' +str(req_id) + ' ' +str(req_stamp), self.sock[self.my_choice['id']]) )
					
		else:
			self.timestamp+=1
			self.msg_queue.put( ("grant "+str(self.node_id)+' '+str(self.timestamp), self.sock[req_id]) )
			self.voted = True
			self.granted = str(req_id)
			self.my_choice['id'] = req_id
			self.my_choice['timestamp'] = req_stamp

	def leave_handler(self, leaving_node):
		self.voted = False
		#check if you have un-replied messages
		if(not self.pending.empty()):
			waiting_node = self.pending.get()
			self.pending.task_done()
			self.timestamp+=1
			self.msg_queue.put(("grant "+str(self.node_id) +' '+str(self.timestamp), self.sock[int(waiting_node[1])]))
			self.voted = True
			self.granted = str(waiting_node[1])
			self.my_choice['timestamp'] = waiting_node[0]
			self.my_choice['id'] = waiting_node[1]
		else:
			self.my_choice['timestamp'] = None
			self.my_choice['id'] = None

	def inquire_handler(self, voter, replacement, replacement_stamp):
		if(self.state !=2 and (self.failed_count > 0 or self.send_stamp > replacement_stamp or (self.send_stamp==replacement_stamp and self.node_id > replacement))):
		#if(self.state !=2 and self.failed_count > 0):
			#yield
			self.reply -=1
			self.failed_count+=1
			#send timestamp
			self.timestamp+=1
			self.msg_queue.put( ("yield " + str(self.node_id) + ' ' +str(self.send_stamp), self.sock[voter]) )

	def yield_handler(self, yielder, yielder_stamp):
		if(not self.pending.empty()):
			waiting_node = self.pending.get()
			#self.pending.task_done()
			self.timestamp+=1
			send_stamp = self.timestamp
			self.msg_queue.put(("grant_yielded "+str(self.node_id) +' '+str(send_stamp), self.sock[int(waiting_node[1])]))
			self.voted = True
			self.granted = str(waiting_node[1])
			self.my_choice['timestamp'] = waiting_node[0]
			self.my_choice['id'] = waiting_node[1]
			#put the yielded node back on the queue
			self.pending.put((yielder_stamp,yielder))

	#def send_msg(self, msg, conn):
	def send_msg(self):
		while(1):
			while(self.msg_queue.empty()==False and self.end == 0):
				msg = self.msg_queue.get()
				self.msg_queue.task_done()
				msg[1].sendall(msg[0] + '\n')

	def maekawa(self):
		#delay to allow connections to be setup
		while len(self.sock) < 9:
			pass
		#start clean after network is setup
		self.timestamp = 0
		algo = threading.Thread(target = self.entry, args = ())
		algo.setDaemon(True)
		algo.start()
		algo.join(float(self.tot_exec_time))
		while(self.state == 2):
			pass
		self.end = 1
		globals.end = 1
		sys.exit()

	def entry(self):
		self.sending_request = True
		self.state = 1
		self.timestamp+=1
		self.send_stamp = self.timestamp
		#self.sendlock.acquire()
		for x in range(1, 10):
			if x in self.my_set:
				self.msg_queue.put( ("REQUEST " + str(self.node_id) +' '+str(self.send_stamp), self.sock[x]) )
		#self.sendlock.release()
		self.sending_request = False
		count = 0
		while(self.reply < 5):
			if self.waited > self.cs_int*2 and self.reply==4:
				for x in self.my_set:
					if x not in self.granters:
						self.msg_queue.put( ("REQUEST " + str(self.node_id) +' '+str(self.send_stamp), self.sock[x]))
			pass
		self.critical_section()

	def critical_section(self):
		print '[%f] [Node %d] %s\n'%(time.time(), self.node_id, self.granters)
		self.state = 2
		time.sleep(float(self.cs_int) / 1000000.0)
		self.leave()

	def leave(self):
		#update flags
		self.state = 3
		self.reply = 0
		self.voted = False
		#print '[Node %d] Leaving CS: time:[%f] \n'%(self.node_id, time.time())
		self.timestamp+=1
		send_stamp = self.timestamp
		#self.sendlock.acquire()
		for x in range(1, 10):
			if x in self.my_set and self.end == 0:
				self.msg_queue.put( ("LEAVING " + str(self.node_id) +' '+str(send_stamp),self.sock[x]) )
		#self.sendlock.release()
		time.sleep(float(self.next_req) / 1000000.0)
		if(not self.end):
			self.entry()
	


