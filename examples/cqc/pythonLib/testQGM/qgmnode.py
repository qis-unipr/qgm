
from bitarray import bitarray
from random import *
from time import sleep
from threading import Thread
from subprocess import call
import sys, os, re, datetime

from SimulaQron.general.hostConfig import *
from SimulaQron.cqc.backend.cqcHeader import *
from SimulaQron.cqc.pythonLib.cqc import *

from protocol import *
from utils import *


##############################
#
# QGMNode class derived from CQCConnection, with reg* attributes
#

class QGMNode():

	def __init__(self, myid, d, p, n, t, l):
		self.myid = myid
		self.myself = 'node'+str(myid)
		self.d = d
		self.p = p
		self.n = n
		self.t = t
		self.l = l
		self.indexes = {}
		self.indexes2 = {}
		
		# Flag to establish when STEP1 has been terminated with all the nodes involved
		self.step1Terminated = 0
		# Flag to determine if there are pending local violations that have yet to be resolved
		self.pendingViolation = 0
		# Flag to determine if the node is executing the protocol
		self.busy = 0
		# Flag to determine if parent node has answered to the child node after his local violation occurred
		self.parentAnsw = 0
		# Flag to determine the number of times the root node has exceeded the threshold
		self.overrunNumber = 0
		
		# Bit registers for local state and global state
		self.regVLocal = bitarray(d)
		self.regVGlobal = bitarray(d)
		
		# Bit register for the variation of the state
		self.regDeltaVLocal = bitarray(d)
		
		# Temporary bit register
		self.tmpregDeltaVLocal = bitarray(d)
		
		# Sign of the variation as child node
		self.sign = ""
		# Dictionary to save each sign of the variation of each child (as parent node)
		self.sign2 = {}
		
		# State after variation update
		self.new_localStateBit = ""
		
		# Dictionary to count the qubits exchanged by the node
		self.excQubits = {'sent':0, 'received':0}
		
		# Dictionary for node identifiers
		self.identifiers = {}
		self.state = {}
		
		# Create qubit registers for EPR pairs shared with child nodes
		self.regA = {}
		self.regAB = {}
		
		# Create qubit registers for EPR pairs shared with the parent node
		self.regB = {}	
		self.regBA = {}
		
		# If the node is different from the root node, it calculates the parent node id
		if (myid != 0):
			# set the identifier of the parent node
			self.identifiers['parent'] = 'node0'
			
			# list of indexes of the parent node
			self.indexes[self.identifiers['parent']] = []
			self.indexes2[self.identifiers['parent']] = []
			
			# set the parent node in the READY state
			self.state[self.identifiers['parent']] = 'READY'
			
			# registers for the qubit that the node shares with the parent node
			self.regB[self.identifiers['parent']] = []
			self.regBA[self.identifiers['parent']] = []
		else:
			self.identifiers['parent'] = 'null'
			for i in range(1, self.n):
				# set the identifier of each child node
				self.identifiers[i] = 'node'+str(i)
				
				# list of indexes for each child node
				self.indexes[self.identifiers[i]] = []
				self.indexes2[self.identifiers[i]] = []
				
				# set each child node in the READY state
				self.state[self.identifiers[i]] = 'READY'
				
				# registers for the qubit that the node shares with his child nodes
				self.regA[self.identifiers[i]] = []
				self.regAB[self.identifiers[i]] = []
				
			# Check if the log and log2 folders exists, otherwise it creates it
			if not os.path.exists("log"):
				os.makedirs("log")
			if not os.path.exists("log2"):
				os.makedirs("log2")
			if not os.path.exists("G12"):
				os.makedirs("G12")
		
		# Initialize the CQC connection
		with CQCConnection(self.myself) as self.node:
		
			# If the node is not the root node (node0), it starts a local processing thread
			if (myid != 0):
				self.startLocalProcessing()

			# Start del listening loop	
			self.listen()
	
	###################################
	#
	#  method for starting the local processing loop in a separate thread
	#
	def startLocalProcessing(self):
		tProc = Thread(target=self.localProcessing, args=())
		tProc.start()
	
	
	###################################
	#
	#  processing loop
	#
	def localProcessing(self):

		# Initialize to 0 the bit register for the local state
		i = 0
		while i < self.d:	
			self.regVLocal[i] = 0
			self.regDeltaVLocal[i] = 0
			i = i+1
					
		# Main loop
		while True:
			to_print = "## [localProcessing] Child {}: current state is {}".format(self.node.name, self.state[self.identifiers['parent']])
			print(to_print)
			
			# If the parent node is in the PROC state, sleep by a random value, double-check that it is still in the PROC state
			# and finally randomly changes some bits of the local state register
			if (self.state[self.identifiers['parent']] == 'PROC'):
				if (self.pendingViolation == 0):
					wt = randint(5,8)
					time.sleep(wt)
				else:
					wt = randint(20,25)
					time.sleep(wt)
				if (self.state[self.identifiers['parent']] == 'PROC'):	 # re-check
					# Check if there is a previous local violation not yet notified
					# If there are none, it normally proceeds, otherwise it manages that pendant
					if (self.pendingViolation == 0):
						# Initialize to 0 the bit register for the local state variation
						i = 0
						while i < self.d:	
							self.tmpregDeltaVLocal[i] = 0
							i = i+1
						# Scroll every bit of the register and changes it only if the random value is less than the value of p
						i = 0
						flag = 0
						while i < self.d/2:
							r = random()
							if r < self.p:
								self.tmpregDeltaVLocal[i*2] = getrandbits(1)
								self.tmpregDeltaVLocal[i*2+1] = getrandbits(1)
							i = i+1
						# 50% probability that the sign is + or -
						tmpsign = ""
						flip = random()
						if flip < 0.5:
							tmpsign = "+"
						else:
							tmpsign = "-"
						# Check if local state +- variation exceed the threshold
						localState = int(self.regVLocal.to01(), 2)
						variation = int(self.tmpregDeltaVLocal.to01(), 2)
						threshold = int(self.t, 2)
						new_localState = 0
						if tmpsign == "+":
							new_localState = localState + variation
						else:
							new_localState = localState - variation
						# Update regDeltaVLocal and the sign only if the new local state is positive
						if (new_localState >= 0 and new_localState <= 255):
							if new_localState > threshold:
								flag = 1
							self.new_localStateBit = str(bin(new_localState)[2:].zfill(self.d))
							i = 0
							while i < self.d:	
								self.regDeltaVLocal[i] = self.tmpregDeltaVLocal[i]
								i = i+1
							self.sign = tmpsign
							# Update log file with the new regVLocal value
							append_write = 'w'
							if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
								append_write = 'a' # append if already exists
							with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
								file.write(str(datetime.datetime.now())+"_"+self.new_localStateBit+"\n")
							to_print = "## Child {}: regVLocal has undergone a change {}".format(self.node.name, self.new_localStateBit)
							print(to_print)

						# If at least one bit has changed it means that there has been a local violation
						if flag == 1:
							# Update log file with the new regVLocal value
							#append_write = 'w'
							#if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
							#	append_write = 'a' # append if already exists
							#with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
							#	file.write(str(datetime.datetime.now())+"_"+self.new_localStateBit+"\n")
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":parent_free"))
							waitLoop = True
							while waitLoop:
								if (self.parentAnsw == 1 or self.parentAnsw == 2):
									waitLoop = False
							# Check if it can notify the local violation
							if (self.parentAnsw == 2):
								to_print = "## PROC ## Child {}: new local state after local violation: {}".format(self.node.name, self.new_localStateBit)
								print(to_print)
								# Notify the parent node of the local violation by sending it a classic message
								self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation:"+self.sign))
								# Update the Bell pair and sends the modified qubits to the parent node starting the protocol STEP2
								self.state[self.identifiers['parent']] = 'STEP2'					
								del self.indexes[self.identifiers['parent']][:] # perform some cleaning
								childStep2(self.node, self.identifiers['parent'], self.regDeltaVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']], self.excQubits)
							else:
								self.pendingViolation = 1
								to_print = "## PROC ## Child {}: local violation occurred but cannot notify now: {}".format(self.node.name, self.new_localStateBit)
								print(to_print)
								time.sleep(8)
							self.parentAnsw = 0
					elif (self.pendingViolation == 1):
						self.parentAnsw = 0
						self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":parent_free"))
						waitLoop = True
						while waitLoop:
							if (self.parentAnsw == 1 or self.parentAnsw == 2):
								waitLoop = False
						# Manage the pending local violation
						if (self.parentAnsw == 2):
							to_print = "## PROC ## Child {}: handling the pending local violation occurred before: {}".format(self.node.name, self.new_localStateBit)
							print(to_print)
							# Notify the parent node of the local violation by sending it a classic message
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation:"+self.sign))
							# Update the Bell pair and sends the modified qubits to the parent node starting the protocol STEP2
							self.state[self.identifiers['parent']] = 'STEP2'					
							del self.indexes[self.identifiers['parent']][:] # perform some cleaning
							childStep2(self.node, self.identifiers['parent'], self.regDeltaVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']], self.excQubits)
							self.pendingViolation = 0
							self.parentAnsw = 0
						else:
							time.sleep(8)
			# If the node status is not in PROC, wait until it returns in that state
			elif (self.state[self.identifiers['parent']] != 'PROC'):
				wt = 10
				time.sleep(wt)


	##############################################
	#
	#  listening loop (starting message handling in a separate thread)
	#
	def listen(self):
		
		# Initialize to 0 the bit register for the global state
		i = 0
		while i < self.d:
			self.regVGlobal[i] = 0	
			i = i+1
		
		# STEP1 management only for the root node
		if (self.myid == 0):
			for i in range(1, self.n):
				self.state[self.identifiers[i]] = 'STEP1'
				parentStep1(self.node, self.identifiers[i], self.regA, self.regAB, self.d, self.excQubits)
				self.state[self.identifiers[i]] = 'WAIT'
				self.node.sendClassical(self.identifiers[i], str.encode(self.myself+":start_step1"))
				data = self.node.recvClassical()
				content = data.decode().split(":")
				sender = content[0]
				msg = content[1]
				to_print = "App {}: received message '{}' from: {}".format(self.node.name, msg, sender)
				print(to_print)
			
			# Notify all child nodes that STEP1 is terminated
			for i in range(1, self.n):
				self.node.sendClassical(self.identifiers[i], str.encode(self.myself+":step1_terminated"))
		
		# Wait to receive a classic message, after which it handles it in a dedicated thread
		while True:
			data = self.node.recvClassical()
			content = data.decode().split(":")
			sender = content[0]
			msg = content[1]
			to_print = "App {}: received message '{}' from: {}".format(self.node.name, msg, sender)
			print(to_print)
			
			# Check the type of the received message
			if (msg == "start_step1"):
				self.state[self.identifiers['parent']] = 'STEP1'
				tComm = Thread(target=self.commHandler, args=(sender, self.regB, self.regBA))
				tComm.start()
			elif (msg == "step1_terminated"):
				self.step1Terminated = 1
			elif (msg == "parent_free"):
				if (self.busy):
					self.node.sendClassical(sender, str.encode(self.myself+":parent_not_free"))
				else:
					self.busy = 1
					self.node.sendClassical(sender, str.encode(self.myself+":parent_is_free"))
			elif (msg == "parent_not_free"):
				self.parentAnsw = 1
			elif (msg == "parent_is_free"):
				self.parentAnsw = 2
			elif (msg == "child_violation"):
				self.sign2[sender] = content[2]
				tComm = Thread(target=self.commHandler, args=(sender, self.regA, self.regAB))
				tComm.start()
			elif (msg == "step2"):
				self.node.sendClassical(sender, str.encode(self.myself+":mysign:"+self.sign))
				tComm = Thread(target=self.commHandler, args=(sender, self.regB, self.regBA))
				tComm.start()
			elif (msg == "mysign"):
				self.sign2[sender] = content[2]
			else:
				# Start a new thread to handle the communication, if the message was sent
				# from the parent node it passes the regB registers and regBA, otherwise regA and regAB
				if (sender == self.identifiers['parent']):
					tComm = Thread(target=self.commHandler, args=(sender, self.regB, self.regBA))
				else:
					tComm = Thread(target=self.commHandler, args=(sender, self.regA, self.regAB))
				tComm.start()

		
	###################################
	#
	#  handler for messages coming from any node
	#
	def commHandler(self, sender, reg1, reg2):
		#to_print = "commHandler - message sender is: {}".format(sender)
		#print(to_print)
	
		### Actions as child node ###
		if (sender == self.identifiers['parent']):
			if (self.state[sender] == 'STEP1'):
				childStep1(self.node, sender, reg1, reg2, self.d, self.excQubits)
				self.node.sendClassical(sender, str.encode(self.myself+":end_step1"))
				# Wait for the parent node to know that it has finished STEP1 with all its child nodes
				waitLoop = True
				while waitLoop:
					if (self.step1Terminated):
						waitLoop = False
				self.state[sender] = 'PROC'
			elif (self.state[sender] == 'PROC'):
				self.busy = 1
				self.state[sender] = 'WAIT'
				to_print = "#### Child {}: forced to {} by {}".format(self.node.name, self.state[sender], sender)
				print(to_print)
			elif (self.state[sender] == 'WAIT'):	
				# Update the Bell pairs and send changed qubits to parent
				self.state[sender] = 'STEP2'
				del self.indexes[sender][:] # perform some cleaning
				childStep2(self.node, sender, self.regDeltaVLocal, reg1, reg2, self.d, self.indexes[sender], self.excQubits)
			elif (self.state[sender] == 'STEP2'):
				self.state[sender] = 'STEP3'
				del self.indexes2[sender][:] # perform some cleaning
				childStep3(self.node, sender, reg1, reg2, self.d, self.indexes[sender], self.indexes2[sender], self.excQubits)
				self.state[sender] = 'STEP4'
				childStep4(self.node, sender, self.regVGlobal, reg1, reg2, self.d, self.indexes2[sender], self.excQubits)
				to_print = "### Child {}: received new global state: {}".format(self.node.name, self.regVGlobal)
				print(to_print)
				# Update regVLocal with the new regVGlobal received from the parent node
				i = 0
				while i < self.d:
					self.regVLocal[i] = self.regVGlobal[i]
					i = i+1
				to_print = "### Child {}: updated local state: {}".format(self.node.name, self.regVLocal)
				print(to_print)
			elif (self.state[sender] == 'STEP4'):
				to_print = "#### Child {}: end protocol notified by {}".format(self.node.name, sender)
				print(to_print)
				
				# Update log file and reset the counter of the qubits exchanged only for the leaf nodes
				append_write = 'w'
				if (os.path.isfile(os.path.join('log2', self.node.name+'.txt'))):
					append_write = 'a' # append if already exists
				with open(os.path.join('log2', self.node.name+'.txt'), append_write) as file:
					file.write(str(datetime.datetime.now())+"_"+self.node.name+"_LV_S:"+str(self.excQubits['sent'])+"_R:"+str(self.excQubits['received'])+"\n")
				self.excQubits['sent'] = 0
				self.excQubits['received'] = 0

				if (self.pendingViolation == 0):
					self.busy = 0
				self.state[sender] = 'PROC'
				
		### Actions as parent node ###
		else:
			if (self.state[sender] == 'WAIT'):
				self.busy = 1
				# Send a classic message to the other child nodes to force them into the WAIT state (assuming they are in the PROC state)
				for i in range(1, self.n):
					if not (self.identifiers[i] == sender):
						self.node.sendClassical(self.identifiers[i], str.encode(self.myself+":wait"))
				
				# Start the parentStep2 with the child node that has notified a local violation
				self.state[sender] = 'STEP2'
				del self.indexes[sender][:] # perform some cleaning
				parentStep2(self.node, sender, reg2, self.d, self.indexes[sender], self.excQubits)
				
				# Send a classic message to the other child nodes to force them into the STEP2 state (assuming they are in the WAIT state)
				for i in range(1, self.n):
					if not (self.identifiers[i] == sender):
						self.node.sendClassical(self.identifiers[i], str.encode(self.myself+":step2"))
						# Start the parentStep2 with the other child node
						self.state[self.identifiers[i]] = 'STEP2'
						del self.indexes[self.identifiers[i]][:] # perform some cleaning
						parentStep2(self.node, self.identifiers[i], reg2, self.d, self.indexes[self.identifiers[i]], self.excQubits)
								
				# Update the global registry
				time.sleep(2)
				to_print = "## 3 ## Parent {}: updating regVGlobal".format(self.node.name)
				print(to_print)	
				# Perform Bell state discrimination by nondestructive measurement 
				# on the local Bell pairs (whose indexes have been saved)
				reg = {}
				for i in range(1, self.n):
					reg[i] = bitarray(self.d)
					j = 0
					while j < self.d:	
						reg[i][j] = 0
						j = j+1
				j = 0
				while j < (self.d)/2:
					for i in range(1, self.n):
						if (j in self.indexes[self.identifiers[i]]):
							# Measure the qubits of the child node that had the local violation
							aq1 = qubit(self.node)
							aq2 = qubit(self.node)
							nondestructiveBellStateDiscrimination(reg1[self.identifiers[i]][j], reg2[self.identifiers[i]][j], aq1, aq2)
							reg[i][j*2] = aq1.measure()
							reg[i][j*2+1] = aq2.measure()
							to_print = "App {}: nbsd of {} --> i, b1, b2: {}, {}, {}".format(self.node.name, self.identifiers[i], j, int(reg[i][j*2]), int(reg[i][j*2+1]))
							print(to_print)
					j = j+1
				# Calculate the new global state from the average of the local states of the n-1 child nodes
				avgIntLocalStates = 0
				state = int(self.regVGlobal.to01(), 2)
				for i in range(1, self.n):
					variation = int(reg[i].to01(), 2)
					if self.sign2[self.identifiers[i]] == "+":
						avgIntLocalStates += (state + variation)
					elif self.sign2[self.identifiers[i]] == "-":
						avgIntLocalStates += (state - variation)
					else:
						avgIntLocalStates += state
					to_print = "avgIntLocalStates after state received from {}: {}".format(self.identifiers[i], avgIntLocalStates)
					print(to_print)
				avgIntLocalStates /= (self.n-1)
				avgBitLocalStates = bin(int(avgIntLocalStates))[2:].zfill(self.d)
				avgBitLocalStatesList = [int(i) for i in str(avgBitLocalStates)]
				i = 0
				while i < self.d:
					self.regVGlobal[i] = avgBitLocalStatesList[i]
					self.regVLocal[i] = avgBitLocalStatesList[i]
					i = i+1
				if (self.myid != 0):
					# Update log file with the new regVLocal value
					append_write = 'w'
					if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
						append_write = 'a' # append if already exists
					with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
						file.write(str(datetime.datetime.now())+"_"+self.regVLocal.to01()+"\n")
				# Print the new v(t) 
				print("New regVGlobal of {}: {}".format(self.node.name, self.regVGlobal))
				print("New regVLocal of {}: {}".format(self.node.name, self.regVLocal))
				time.sleep(3)		
				
				# Start parentStep3 and parentStep4 with each child node (first one, then the other)
				# Current child node
				self.state[sender] = 'STEP3'
				self.node.sendClassical(sender, str.encode(self.myself+":step3")) # wake up sender to STEP3
				del self.indexes2[sender][:] # perform some cleaning
				parentStep3(self.node, sender, self.regVGlobal, reg1, reg2, self.d, self.indexes[sender], self.indexes2[sender], self.excQubits)
				self.state[sender] = 'STEP4'
				parentStep4(self.node, sender, reg1, reg2, self.d, self.indexes2[sender], self.excQubits)
				self.state[sender] = 'WAIT'
											  
				for i in range(1, self.n):
					if not (self.identifiers[i] == sender):
						# Other child node
						time.sleep(2)
						self.state[self.identifiers[i]] = 'STEP3'
						self.node.sendClassical(self.identifiers[i], str.encode(self.myself+":step3")) # wake up other child to STEP3
						del self.indexes2[self.identifiers[i]][:] # perform some cleaning
						parentStep3(self.node, self.identifiers[i], self.regVGlobal, reg1, reg2, self.d, self.indexes[self.identifiers[i]], self.indexes2[self.identifiers[i]], self.excQubits)
						self.state[self.identifiers[i]] = 'STEP4'
						parentStep4(self.node, self.identifiers[i], reg1, reg2, self.d, self.indexes2[self.identifiers[i]], self.excQubits)
						self.state[self.identifiers[i]] = 'WAIT'
				
				time.sleep(1)
				
				# Log G12
				append_write = 'w'
				if (os.path.isfile(os.path.join('G12', 'G12.txt'))):
					append_write = 'a' # append if already exists
				with open(os.path.join('G12', 'G12.txt'), append_write) as file:
					file.write(str(datetime.datetime.now())+"_"+str(int(self.regVGlobal.to01(), 2))+"\n")
				
				self.overrunNumber += 1
				
				# Check if the threshold has been exceeded
				if (int(self.regVGlobal.to01(),2) > int(self.t,2)):
					# Notify the end of the protocol to the child nodes
					for i in range(1, self.n):
						self.node.sendClassical(self.identifiers[i], str.encode(self.node.name+":protocol_terminated"))
					time.sleep(2)
					
					if (self.myid == 0):
						print("*** G12 in the root node has exceeded the threshold: timestamp saved. ***")
						# Update log file about the local state
						append_write = 'w'
						if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
							append_write = 'a' # append if already exists
						with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
							file.write(str(datetime.datetime.now())+"_"+self.regVLocal.to01()+"\n")
							
						# Update log file and reset the counter of the qubits exchanged
						append_write = 'w'
						if (os.path.isfile(os.path.join('log2', self.node.name+'.txt'))):
							append_write = 'a' # append if already exists
						with open(os.path.join('log2', self.node.name+'.txt'), append_write) as file:
							file.write(str(datetime.datetime.now())+"_"+self.node.name+"_root"+"_S:"+str(self.excQubits['sent'])+"_R:"+str(self.excQubits['received'])+"\n")
						self.excQubits['sent'] = 0
						self.excQubits['received'] = 0
					else:
						print("Parent {}: threshold has been exceeded.".format(self.node.name))
						
					if (self.overrunNumber == self.l):
						call(["killall", "python3"])
					
					if (self.myid != 0):
						self.pendingViolation = 1
					else:
						self.busy = 0
				else:
					# Threshold not exceeded
					# Notify the end of the protocol to the child nodes
					for i in range(1, self.n):
						self.node.sendClassical(self.identifiers[i], str.encode(self.node.name+":protocol_terminated"))
					self.busy = 0
					
					if (self.overrunNumber == self.l):
						call(["killall", "python3"])
					

##############################
#
# main   
#
def main():

	print('Number of arguments:', len(sys.argv), 'arguments.')
	print('Argument List:', str(sys.argv))

	# Node id
	myid = int(sys.argv[1])
	# Probability of local violation
	p = round(float(sys.argv[2]),1)
	# d value
	d = 8
	# Number of nodes
	n = 7
	# Threshold
	t = '01111111'
	# Max number of root node threshold violation
	l = 50
	qgmnode = QGMNode(myid, d, p, n, t, l)
	print(qgmnode.identifiers)
		
		
##############################		
main()