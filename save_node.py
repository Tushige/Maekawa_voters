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
		self.yielded = {}
		self.timestamp = 0
		self.failed_count = 0
		#*****
		#Begin Node setup
		#*****
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
					#self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					peer_id = int(buf[1])
					self.sock[peer_id] = conn
		
				elif(buf[0] == "REQUEST"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.lock.acquire()
					self.request_handler(int(buf[1]), int(buf[2]))
					self.lock.release()

				elif(buf[0] == "LEAVING"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.leave_handler(int(buf[2]))

				elif(buf[0] == "grant"):
					self.reply +=1
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					#print '[Node %d] received %dth reply from %d \n'%(self.node_id, self.reply, int(buf[1]))

				elif(buf[0] == "grant_yielded"):
					self.reply +=1
					self.failed_count -=1
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)

				elif(buf[0] == "inquire"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.inquire_handler(int(buf[1]), int(buf[3]))

				elif(buf[0] == "yield"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.yield_handler(int(buf[1]))

				elif(buf[0] == "failed"):
					self.timestamp = max(self.timestamp+1, int(buf[2])+1)
					self.failed_count+=1
					print '[Node %d] received Failed from %d\n'%(self.node_id, int(buf[1]))
		conn.close()
		#s_server.close()

	def request_handler(self, req_id, req_stamp):
		#don't process others' request until mine has been sent
		while(self.sending_request == True):
			pass
		choose_myself = (self.state == 1 and (self.timestamp < req_stamp or (self.timestamp==req_stamp and self.node_id < req_id)))
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
					self.yielded[self.my_choice['id']] = req_id
		else:
			self.timestamp+=1
			self.send_msg("grant "+str(self.node_id)+' '+str(self.timestamp), self.sock[req_id])
			print '[Node %d] voted for %d\n'%(self.node_id, req_id)
			self.voted = True
			self.my_choice['id'] = req_id
			self.my_choice['timestamp'] = req_stamp

	def leave_handler(self, req_stamp):
		self.voted = False
		#check if you have un-replied messages
		if(not self.pending.empty()):
			waiting_node = self.pending.get()
			self.pending.task_done()
			self.timestamp+=1
			self.send_msg("grant "+str(self.node_id) +' '+str(self.timestamp), self.sock[int(waiting_node[1])])
			print '[Node %d] voted for %d\n'%(self.node_id, waiting_node[1])
			self.voted = True
			self.my_choice['timestamp'] = waiting_node[0]
			self.my_choice['id'] = waiting_node[1]

	def inquire_handler(self, voter, replacement):
		if(self.failed_count > 0):
			#yield
			self.reply -=1
			#send timestamp
			self.timestamp+=1
			self.send_msg("yield " + str(self.node_id) + ' ' +str(self.timestamp), self.sock[voter])
			#print '[Node %d] i\'m yielding to %d by node %d\'s request\n'%(self.node_id,replacement, voter)
			return
		#print '[Node %d] i\'m NOT yielding to %d by node %d\'s request\n'%(self.node_id, replacement, voter)

	def yield_handler(self, yielder):
		if(not self.pending.empty()):
			waiting_node = self.pending.get()
			self.pending.task_done()
			self.timestamp+=1
			#print '[Node %d] node %d no longer yielded \n'%(self.node_id, waiting_node[1])
			self.send_msg("grant_yielded "+str(self.node_id) +' '+str(self.timestamp), self.sock[int(waiting_node[1])])
			#print '[Node %d] received yield from %d, now replying to %d \n'%(self.node_id, yielder, self.yielded[yielder])
			print '[Node %d] received yield from %d, now replying to %d \n'%(self.node_id, yielder, waiting_node[1])
			self.voted = True
			self.my_choice['timestamp'] = waiting_node[0]
			self.my_choice['id'] = waiting_node[1]

	def send_msg(self, msg, conn):
		#print '[Node %d] sending Hi'%self.node_id
		conn.sendall('Start'+msg+'End')

	def start_algorithm(self):
		algo = threading.Thread(target = self.maekawa, args = ())
		#delay to allow connections to be setup
		time.sleep(2.0)
		algo.start()
		#print '[Node %d] '%self.node_id +  str(self.sock.keys())

	def maekawa(self):
		#start clean after network is setup
		self.timestamp = 0
		self.entry()

	def entry(self):
		self.sending_request = True
		self.state = 1
		self.timestamp+=1
		send_stamp = self.timestamp
		print '[Node %d] Requesting Entry with timestamp %d from '%(self.node_id, send_stamp) + str(globals.sets[self.node_id]) + '\n'
		for x in range(1, 10):
			if(x in self.my_set):
				self.send_msg("REQUEST " + str(self.node_id) +' '+str(send_stamp), self.sock[x])
		#update my timestamp
		self.sending_request = False
		
		while(self.reply < 5):
			pass
		self.critical_section()
		self.leave()

	def critical_section(self):
		print '[Node %d] Entering CS: time:%f '%(self.node_id, time.time()) + '\n'
		self.state = 2
		time.sleep(float(self.cs_int))

	def leave(self):
		#update flags
		self.state = 3
		self.reply = 0
		self.voted = False
		print '[Node %d] Leaving CS: time:%f \n'%(self.node_id, time.time())
		self.timestamp+=1
		send_stamp = self.timestamp
		for x in range(1, 10):
			if(x in self.my_set):
				self.send_msg("LEAVING " + str(self.node_id) +' '+str(send_stamp), self.sock[x])
		time.sleep(float(self.next_req))
		self.entry()






