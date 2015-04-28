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
		#*****
		# node instance variables
		#*****
		self.node_id = node_id
		self.cs_int = cs_int
		self.next_req = next_req
		self.tot_exec_time = tot_exec_time

		self.voted = False
		self.my_set = set
		self.pending = Queue.PriorityQueue()
		self.sending_request = False
		self.lock = threading.Lock()
		self.state = 0 #0: init, 1: Request, 2: Held, 3: Release
		self.sock = {}
		self.reply = 0
		self.my_choice = {}
		self.send_stamp = 0
		self.timestamp = 0
		self.failed_count = 0
		self.granters = ''
		self.granted = ''
		self.CS_count = 0
		self.end = 0
		#*****
		#Begin Node setup
		#*****
		try:
			globals.node_obj[self.node_id] = self
		except:
			print self.node_id
		self.start_server()
		self.start_client()
		self.maekawa()

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
				#print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1] + '\n'
				sys.exit();
			self.sock[x].connect((globals.ip, peer_port))

			#self.timestamp+=1
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
			#print '[[ Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1] + ' ]]'
			sys.exit()
		s_server.listen(10)
		while(not self.end):
			conn, addr = s_server.accept()
			r_thread = threading.Thread(target = self.recvThread, args = (conn,))
			r_thread.start()
		s_server.close()

	def recvThread(self, conn):
		while(not self.end):
			try:
				data = conn.recv(1024)
			except:
				print '[NODE %d]**********OMG WHAT THE!!!*************'%self.node_id
				continue
			if len(data) == 0:
				continue
			while data[-1] != '\n':
				data = data + conn.recv(1024)
			messages = data.split('\n')
			for ss in messages:
				buf = ss.split(' ')
				if(buf[0] == ''):
					continue
				if(buf[0] == "hi"):
					#self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					peer_id = int(buf[1])
					self.sock[peer_id] = conn
				elif(buf[0] == "update"):
					self.timestamp = max(self.timestamp+1, int(buf[1])+1)
		
				elif(buf[0] == "REQUEST"):
					#print '[Node %d] received request to enter CS\n'%self.node_id
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)

					self.lock.acquire()
					self.request_handler(int(buf[1]), int(buf[2]))
					self.lock.release()
					#print '[Node %d] fulfilled request\n'%self.node_id

				elif(buf[0] == "LEAVING"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.leave_handler(int(buf[1]))

				elif(buf[0] == "grant"):
					self.reply +=1
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					if(self.granters == ''):
						self.granters = buf[1]
					else:
						self.granters= self.granters + ' '+buf[1]

				elif(buf[0] == "grant_yielded"):
					self.reply +=1
					self.failed_count -=1
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					if(self.granters == ''):
						self.granters = buf[1]
					else:
						self.granters= self.granters + ' '+buf[1]

				elif(buf[0] == "inquire"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.inquire_handler(int(buf[1]), int(buf[3]))

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
		choose_myself = (self.state == 1 and (self.send_stamp < req_stamp or (self.timestamp==req_stamp and self.node_id < req_id)))
		if(self.state == 2 or self.voted == True or choose_myself):
			self.pending.put((req_stamp, req_id)) # queue the message
			self.timestamp+=1
			self.send_msg('failed ' +str(self.node_id) + ' ' + str(self.timestamp), self.sock[req_id])
			#check if the requester has higher priority than my current choice
			if(self.voted == True):
				if(req_stamp < self.my_choice['timestamp'] or (req_stamp == self.my_choice['timestamp'] and req_id < self.my_choice['id'])):
					#if new request has higher priority than my accepted request
					self.timestamp+=1
					self.send_msg("inquire " + str(self.node_id) +' ' + str(self.timestamp) + ' ' +str(req_id), self.sock[self.my_choice['id']])
		else:
			self.timestamp+=1
			self.send_msg("grant "+str(self.node_id)+' '+str(self.timestamp), self.sock[req_id])
			#print '[Node %d] voted for %d\n'%(self.node_id, req_id)
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
			self.send_msg("grant "+str(self.node_id) +' '+str(self.timestamp), self.sock[int(waiting_node[1])])
			#print '[Node %d] voted for %d \n'%(self.node_id, waiting_node[1])
			self.voted = True
			self.granted = str(waiting_node[1])
			self.my_choice['timestamp'] = waiting_node[0]
			self.my_choice['id'] = waiting_node[1]
		else:
			self.my_choice['timestamp'] = None
			self.my_choice['id'] = None

	def inquire_handler(self, voter, replacement):
		if(self.failed_count > 0):
			#yield
			self.reply -=1
			#send timestamp
			self.timestamp+=1
			self.send_msg("yield " + str(self.node_id) + ' ' +str(self.timestamp), self.sock[voter])
			#print '[Node %d] i\'m yielding to %d by node %d\'s request\n'%(self.node_id,replacement, voter)
			remove_idx = self.granters.find(str(voter))
			#remove voter from list of granters
			self.granters = self.granters[0:remove_idx] + self.granters[remove_idx+2:len(self.granters)]
			return
		else:
			print '[Node %d] i\'m NOT yielding to %d by node %d\'s request\n'%(self.node_id,replacement, voter)

	def yield_handler(self, yielder, yielder_stamp):
		if(not self.pending.empty()):
			waiting_node = self.pending.get()
			self.pending.task_done()
			self.timestamp+=1
			self.send_msg("grant_yielded "+str(self.node_id) +' '+str(self.timestamp), self.sock[int(waiting_node[1])])
			self.voted = True
			self.granted = str(waiting_node[1])
			self.my_choice['timestamp'] = waiting_node[0]
			self.my_choice['id'] = waiting_node[1]
			print '[Node %d] received yield from %d, now replying to %d \n'%(self.node_id, yielder, waiting_node[1])
			#put the yielded node back on the queue
			self.pending.put((yielder_stamp,yielder))

	def send_msg(self, msg, conn):
		#print '[Node %d] sending Hi'%self.node_id
		if(conn != None):
			conn.sendall(msg+'\n')
		else:
			print '*********############WHOAAAA##########**********\n'
	def update(self):
		for x in range(1,len(self.sock)+1):
			self.send_msg("update " + str(self.timestamp), self.sock[x])

	def maekawa(self):
		#delay to allow connections to be setup
		while len(self.sock) < 9:
			pass
		#start clean after network is setup
		self.timestamp = 0
		upd_t = threading.Thread(target = self.update, args = ())
		upd_t.start()
		algo = threading.Thread(target = self.entry, args = ())
		algo.start()
		algo.join(float(self.tot_exec_time))
		while(self.state == 2):
			pass
		self.end = 1
		globals.end = 1
		print '***********[Node %d] Quit***********\n'%self.node_id

		sys.exit()

	def entry(self):
		self.sending_request = True
		self.state = 1
		self.timestamp+=1
		self.send_stamp = self.timestamp
		print '[Node %d] Requesting Entry with timestamp %d from '%(self.node_id, self.send_stamp) + str(globals.sets[self.node_id]) + '\n'
		for x in range(1, 10):
			if x in self.my_set:
				self.send_msg("REQUEST " + str(self.node_id) +' '+str(self.send_stamp), self.sock[x])
		#update my timestamp
		self.sending_request = False
		
		while(self.reply < 5):
			pass
		self.critical_section()
		self.leave()

	def critical_section(self):
		print '[Node %d] Entering CS: %d time:[%f] voters: [%s] voted: [%s]'%(self.node_id, self.CS_count, time.time(), self.granters, self.granted) + '\n'
		self.CS_count +=1
		self.state = 2
		time.sleep(float(self.cs_int))

	def leave(self):
		#update flags
		self.state = 3
		self.reply = 0
		self.voted = False
		self.granters= ''
		print '[Node %d] Leaving CS: time:[%f] \n'%(self.node_id, time.time())
		self.timestamp+=1
		send_stamp = self.timestamp
		for x in range(1, 10):
			if x in self.my_set and self.end == 0:
				self.send_msg("LEAVING " + str(self.node_id) +' '+str(send_stamp), self.sock[x])
		time.sleep(float(self.next_req))
		if(not self.end):
			self.entry()

	def show(self):
		print '[Node %d] '%self.node_id + self.granters + '\n'
	


