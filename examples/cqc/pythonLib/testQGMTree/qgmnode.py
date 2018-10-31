
from bitarray import bitarray
from random import *
from time import sleep
from threading import Thread
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

	def __init__(self, myid, d, p, n, t):
		self.myid = myid
		self.myself = 'node'+str(myid)
		self.d = d
		self.p = p
		self.n = n
		self.t = t
		self.indexes = {}
		
		# Number of child nodes that responded to having finished STEP1
		self.numChildAnsw = 0
		# Flag to establish when STEP1 has been terminated with all the nodes involved
		self.step1Terminated = 0
		# Flag to determine when to execute STEP1 as a parent node
		self.startStep1AsParent = 0
		# Flag to determine when the parent node can start STEP1 with the right child node
		self.step1rightChild = 0
		# Flag to determine if a local violation can be notified
		self.notifyFlag = 0
		# Flag to determine if there are pending local violations that have yet to be resolved
		self.pendingViolation = 0
		# Flag to determine if the current node is a leaf node
		self.leafNode = 0
		# Flag to determine if the node is executing the protocol
		self.busy = 0
		# Flag to determine if parent node has answered to the child node after his local violation occurred
		self.parentAnsw = 0
		# Flag to determine if the other node is waiting because it gave precedence to the current node
		self.otherChildPending = 0
		
		# Bit registers for local state and global state
		self.regVLocal = bitarray(d)
		self.regVGlobal = bitarray(d)
		
		# Dictionary to count the qubits exchanged by the node
		self.excQubits = {'sent':0, 'received':0}
		
		# Dictionary for node identifiers
		self.identifiers = {'parent':'unknown', 'leftChild':'unknown', 'rightChild':'unknown'}
		self.state = {}
		
		# If the node is different from the root node, it calculates the parent node id
		if (myid != 0):
			idp = 0
			if (myid%2 == 0):
				idp = int((myid - 2)/2)
			elif (myid%2 == 1):
				idp = int((myid - 1)/2)	
			# set the identifier of the parent node
			self.identifiers['parent'] = 'node'+str(idp)
			# set the parent node in the READY state
			self.state[self.identifiers['parent']] = 'READY'
		else:
			self.identifiers['parent'] = 'null'
			# Check if the log folder exists, otherwise it creates it
			if not os.path.exists("log"):
				os.makedirs("log")
		
		# Set the name of the two child nodes if they exist, otherwise they are set to null
		if (myid*2+1 < n):
			self.identifiers['leftChild'] = 'node'+str(myid*2+1)
			self.identifiers['rightChild'] = 'node'+str(myid*2+2)
		else:
			self.identifiers['leftChild'] = 'null'
			self.identifiers['rightChild'] = 'null'
			self.leafNode = 1
		
		# If it's a leaf node, set to 1 the notifyFlag
		if (self.leafNode):
			self.notifyFlag = 1
		
		# List of indexes for the parent node and the two child nodes
		self.indexes[self.identifiers['parent']] = []
		self.indexes[self.identifiers['leftChild']] = []
		self.indexes[self.identifiers['rightChild']] = []
		
		# Set the two child nodes in the READY state
		self.state = {}
		self.state[self.identifiers['leftChild']] = 'READY'
		self.state[self.identifiers['rightChild']] = 'READY'
		
		# Create qubit registers for EPR pairs shared with child nodes
		self.regA = {}
		self.regA[self.identifiers['leftChild']] = [] # for the qubits that the node shares (entangled) with his left child
		self.regA[self.identifiers['rightChild']] = [] # for the qubits that the node shares (entangled) with his right child
		self.regAB = {}
		self.regAB[self.identifiers['leftChild']] = [] # for the qubits that arrive from the left child
		self.regAB[self.identifiers['rightChild']] = [] # for the qubits that arrive from the right child
		
		# Create qubit registers for EPR pairs shared with the parent node
		self.regB = {}	
		self.regBA = {}
		self.regB[self.identifiers['parent']] = []
		self.regBA[self.identifiers['parent']] = []
		
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
			i = i+1
		
		# Wait to execute STEP1 with the parent node
		waitLoop = True
		while waitLoop:
			if (self.startStep1AsParent):
				waitLoop = False
		# If it has child nodes, send a classic message to the left child node to tell it to start STEP1
		if (self.myid*2+2 < self.n):
			self.state[self.identifiers['leftChild']] = 'STEP1'
			parentStep1(self.node, self.identifiers['leftChild'], self.regA, self.regAB, self.d, self.excQubits)
			self.state[self.identifiers['leftChild']] = 'WAIT'
			self.node.sendClassical(self.identifiers['leftChild'], str.encode(self.myself+":start_step1"))
			# Wait until STEP1 finishes with the left child node
			waitLoop = True
			while waitLoop:
				if (self.step1rightChild):
					waitLoop = False
			# STEP1 start with the right child node
			self.state[self.identifiers['rightChild']] = 'STEP1'
			parentStep1(self.node, self.identifiers['rightChild'], self.regA, self.regAB, self.d, self.excQubits)
			self.state[self.identifiers['rightChild']] = 'WAIT'
			self.node.sendClassical(self.identifiers['rightChild'], str.encode(self.myself+":start_step1"))
			# Wait until STEP1 finishes with the right child node
			waitLoop = True
			while waitLoop:
				if (self.numChildAnsw == 2):
					waitLoop = False
			self.numChildAnsw = 0
			# Notify the two child nodes that STEP1 has been terminated with both
			self.node.sendClassical(self.identifiers['leftChild'], str.encode(self.myself+":step1_terminated"))
			self.node.sendClassical(self.identifiers['rightChild'], str.encode(self.myself+":step1_terminated"))
					
		# Main loop
		while True:
			to_print = "## [localProcessing] Child {}: current state is {}".format(self.node.name, self.state[self.identifiers['parent']])
			print(to_print)
			
			# If the parent node is in the PROC state, sleep by a random value, double-check that it is still in the PROC state
			# and finally randomly changes some bits of the local state register
			if (self.state[self.identifiers['parent']] == 'PROC'):
				if (self.pendingViolation == 0):
					wt = random()*60
					time.sleep(wt)
				else:
					time.sleep(3)
				if (self.state[self.identifiers['parent']] == 'PROC'):	 # re-check
					# Check if there is a previous local violation not yet notified
					# If there are none, it normally proceeds, otherwise it manages that pendant
					if (self.pendingViolation == 0 and self.leafNode == 1):
						# Scroll every bit of the register and changes it only if the random value is less than the value of p
						i = 0
						flag = 0
						while i < self.d:
							r = random()
							if r < self.p:
								if self.regVLocal[i] == 1:
									self.regVLocal[i] = 0
								elif self.regVLocal[i] == 0:
									self.regVLocal[i] = 1
								flag = 1
							i = i+1	

						# If at least one bit has changed it means that there has been a local violation
						if flag == 1:
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":only_parent_free"))
							waitLoop = True
							while waitLoop:
								if (self.parentAnsw == 1 or self.parentAnsw == 2):
									waitLoop = False
							# Check if it can notify the local violation
							if (self.parentAnsw == 2):
								to_print = "## PROC ## Child {}: new local state after local violation: {}".format(self.node.name, self.regVLocal)
								print(to_print)
								# Notify the parent node of the local violation by sending it a classic message
								self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation"))
								# Update the Bell pair and sends the modified qubits to the parent node starting the protocol STEP2
								self.state[self.identifiers['parent']] = 'STEP2'					
								del self.indexes[self.identifiers['parent']][:] # perform some cleaning
								childStep2(self.node, self.identifiers['parent'], self.regVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']], self.excQubits)
							else:
								self.pendingViolation = 1
								to_print = "## PROC ## Child {}: local violation occurred but cannot notify now: {}".format(self.node.name, self.regVLocal)
								print(to_print)
								time.sleep(8)
							self.parentAnsw = 0
					elif (self.pendingViolation == 1 and self.leafNode == 1):
						self.parentAnsw = 0
						self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":only_parent_free"))
						waitLoop = True
						while waitLoop:
							if (self.parentAnsw == 1 or self.parentAnsw == 2):
								waitLoop = False
						# Manage the pending local violation
						if (self.parentAnsw == 2):
							to_print = "## PROC ## Child {}: handling the pending local violation occurred before: {}".format(self.node.name, self.regVLocal)
							print(to_print)
							# Notify the parent node of the local violation by sending it a classic message
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation"))
							# Update the Bell pair and sends the modified qubits to the parent node starting the protocol STEP2
							self.state[self.identifiers['parent']] = 'STEP2'					
							del self.indexes[self.identifiers['parent']][:] # perform some cleaning
							childStep2(self.node, self.identifiers['parent'], self.regVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']], self.excQubits)
							self.pendingViolation = 0
							self.parentAnsw = 0
						else:
							time.sleep(8)
					elif (self.pendingViolation == 1 and self.leafNode == 0):
						# Ask to the parent node if it's free
						self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":free_parent_req"))
						# If the parent node is not free retry after 6 seconds, otherwise proceed
						waitLoop = True
						while waitLoop:
							if (self.notifyFlag):
								waitLoop = False
							else:
								time.sleep(6)
								if (self.notifyFlag == 0):
									self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":free_parent_req"))
						self.notifyFlag = 0
						to_print = "## PROC ## Child {}: threshold exceeded synchronization with the parent: {}".format(self.node.name, self.regVLocal)
						print(to_print)
						# Notify the parent node of the local violation by sending it a classic message
						self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation"))
						# Update the Bell pair and sends the modified qubits to the parent node starting the protocol STEP2
						self.state[self.identifiers['parent']] = 'STEP2'					
						del self.indexes[self.identifiers['parent']][:] # perform some cleaning
						childStep2(self.node, self.identifiers['parent'], self.regVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']], self.excQubits)
						self.pendingViolation = 0
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
			# Left child node
			self.state[self.identifiers['leftChild']] = 'STEP1'
			parentStep1(self.node, self.identifiers['leftChild'], self.regA, self.regAB, self.d, self.excQubits)
			self.state[self.identifiers['leftChild']] = 'WAIT'
			self.node.sendClassical(self.identifiers['leftChild'], str.encode(self.myself+":start_step1"))
			data = self.node.recvClassical()
			content = data.decode().split(":")
			sender = content[0]
			msg = content[1]
			to_print = "App {}: received message '{}' from: {}".format(self.node.name, msg, sender)
			print(to_print)
			# Right child node
			self.state[self.identifiers['rightChild']] = 'STEP1'
			parentStep1(self.node, self.identifiers['rightChild'], self.regA, self.regAB, self.d, self.excQubits)
			self.state[self.identifiers['rightChild']] = 'WAIT'
			self.node.sendClassical(self.identifiers['rightChild'], str.encode(self.myself+":start_step1"))
			# Wait to receive the response from the right child node
			data = self.node.recvClassical()
			content = data.decode().split(":")
			sender = content[0]
			msg = content[1]
			to_print = "App {}: received message '{}' from: {}".format(self.node.name, msg, sender)
			print(to_print)
			# Notify both child nodes that STEP1 is terminated
			self.node.sendClassical(self.identifiers['leftChild'], str.encode(self.myself+":step1_terminated"))
			self.node.sendClassical(self.identifiers['rightChild'], str.encode(self.myself+":step1_terminated"))
		
		# Wait to receive a classic message, after which it handles it in a dedicated thread
		while True:
			data = self.node.recvClassical()
			content = data.decode().split(":")
			sender = content[0]
			msg = content[1]
			to_print = "App {}: received message '{}' from: {}".format(self.node.name, msg, sender)
			print(to_print)
			
			# Calculate the name of the other child node
			otherChild = 'temp'
			if (sender == self.identifiers['leftChild']):
				otherChild = self.identifiers['rightChild']
			else:
				otherChild = self.identifiers['leftChild']
			
			# Check the type of the received message
			if (msg == "start_step1"):
				self.state[self.identifiers['parent']] = 'STEP1'
				tComm = Thread(target=self.commHandler, args=(sender, self.regB, self.regBA))
				tComm.start()
			elif (msg == "end_step1"):
				self.step1rightChild = 1
				self.numChildAnsw += 1
			elif (msg == "step1_terminated"):
				self.step1Terminated = 1
			elif (msg == "free_parent_req"):
				if (self.busy):
					self.node.sendClassical(sender, str.encode(self.myself+":parent_not_free"))
				else:
					self.busy = 1
					self.node.sendClassical(otherChild, str.encode(self.myself+":free_child_req"))
			elif (msg == "free_child_req"):
				if (self.busy == 1 and self.pendingViolation == 0):
					if (self.otherChildPending):
						self.node.sendClassical(sender, str.encode(self.myself+":child_is_free"))
						self.otherChildPending = 0
					else:
						self.node.sendClassical(sender, str.encode(self.myself+":child_not_free"))
				elif (self.busy == 1 and self.pendingViolation == 1):
					self.node.sendClassical(sender, str.encode(self.myself+":child_not_free_in_pending"))
				else:
					self.busy = 1
					self.node.sendClassical(sender, str.encode(self.myself+":child_is_free"))
			elif (msg == "child_is_free"):
				self.node.sendClassical(otherChild, str.encode(self.myself+":parent_is_free"))
			elif (msg == "child_not_free"):
				self.busy = 0
				self.node.sendClassical(otherChild, str.encode(self.myself+":parent_not_free"))
			elif (msg == "child_not_free_in_pending"):
				match = re.match(r"([a-z]+)([0-9]+)", otherChild, re.I)
				if match:
					items = match.groups()
					# the odd node takes precedence if the other node is also pending
					if (int(items[1])%2 == 1):
						self.node.sendClassical(otherChild, str.encode(self.myself+":parent_is_free_in_pending"))
					else:
						self.busy = 0
						self.node.sendClassical(otherChild, str.encode(self.myself+":parent_not_free"))
			elif (msg == "parent_not_free"):
				self.notifyFlag = 0
			elif (msg == "parent_is_free"):
				self.notifyFlag = 1
			elif (msg == "parent_is_free_in_pending"):
				self.otherChildPending = 1
				self.notifyFlag = 1
			elif (msg == "only_parent_free"):
				if (self.busy):
					self.node.sendClassical(sender, str.encode(self.myself+":parent_only_not_free"))
				else:
					self.busy = 1
					self.node.sendClassical(sender, str.encode(self.myself+":parent_only_is_free"))
			elif (msg == "parent_only_not_free"):
				self.parentAnsw = 1
			elif (msg == "parent_only_is_free"):
				self.parentAnsw = 2
			elif (msg == "child_violation"):
				tComm = Thread(target=self.commHandler, args=(sender, self.regA, self.regAB))
				tComm.start()
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
				self.startStep1AsParent = 1
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
				childStep2(self.node, sender, self.regVLocal, reg1, reg2, self.d, self.indexes[sender], self.excQubits)
			elif (self.state[sender] == 'STEP2'):
				self.state[sender] = 'STEP3'
				childStep3(self.node, sender, reg1, reg2, self.d, self.indexes[sender], self.excQubits)
				self.state[sender] = 'STEP4'
				childStep4(self.node, sender, self.regVGlobal, reg1, reg2, self.d, self.excQubits)	
			elif (self.state[sender] == 'STEP4'):
				to_print = "#### Child {}: end protocol notified by {}".format(self.node.name, sender)
				print(to_print)
				if (self.leafNode):
					# Update log file and reset the counter of the qubits exchanged only for the leaf nodes
					append_write = 'w'
					if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
						append_write = 'a' # append if already exists
					with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
						file.write(str(datetime.datetime.now())+"_"+self.node.name+"_LV_S:"+str(self.excQubits['sent'])+"_R:"+str(self.excQubits['received'])+"\n")
						self.excQubits['sent'] = 0
						self.excQubits['received'] = 0
				if (self.pendingViolation == 0 and self.otherChildPending == 0):
					self.busy = 0
				self.state[sender] = 'PROC'
				
		### Actions as parent node ###
		else:
			# Establish who is the brother node of the one who sent a message to the parent node
			otherChild = 'temp'
			if (sender == self.identifiers['leftChild']):
				otherChild = self.identifiers['rightChild']
			else:
				otherChild = self.identifiers['leftChild']
			
			if (self.state[sender] == 'WAIT'):
				self.busy = 1
				# Send a classic message to the other child node to force it into the WAIT state (assuming it is in the PROC state)
				self.node.sendClassical(otherChild, str.encode(self.myself+":wait"))				
				# Start the parentStep2 with the child node that has notified a local violation
				self.state[sender] = 'STEP2'
				del self.indexes[sender][:] # perform some cleaning
				parentStep2(self.node, sender, reg2, self.d, self.indexes[sender], self.excQubits)
				
				# Send a classic message to the other child node to force it into the STEP2 state (assuming it is in the WAIT state)
				self.node.sendClassical(otherChild, str.encode(self.myself+":step2"))
				# Start the parentStep2 with the other child node
				self.state[otherChild] = 'STEP2'
				del self.indexes[otherChild][:] # perform some cleaning
				parentStep2(self.node, otherChild, reg2, self.d, self.indexes[otherChild], self.excQubits)
								
				# Update the global registry
				time.sleep(2)
				to_print = "## 3 ## Parent {}: updating regVGlobal".format(self.node.name)
				print(to_print)	
				# Perform Bell state discrimination by nondestructive measurement 
				# on the local Bell pairs (whose indexes have been saved)
				print("Sender indexes size: {}".format(len(self.indexes[sender])))
				print("OtherChild indexes size: {}".format(len(self.indexes[otherChild])))
				regSender = bitarray(self.d)
				regOtherChild = bitarray(self.d)
				i = 0
				while i < self.d:	
					regSender[i] = 0
					regOtherChild[i] = 0
					i = i+1
				i = 0
				while i < (self.d)/2:
					if (i in self.indexes[sender]):
						# Measure the qubits of the child node that had the local violation
						aq1_sender = qubit(self.node)
						aq2_sender = qubit(self.node)
						nondestructiveBellStateDiscrimination(reg1[sender][i], reg2[sender][i], aq1_sender, aq2_sender)
						regSender[i*2] = aq1_sender.measure()
						regSender[i*2+1] = aq2_sender.measure()
					if (i in self.indexes[otherChild]):
						# Measure the qubits of the other child node
						aq1_otherChild = qubit(self.node)
						aq2_otherChild = qubit(self.node)
						nondestructiveBellStateDiscrimination(reg1[otherChild][i], reg2[otherChild][i], aq1_otherChild, aq2_otherChild)
						regOtherChild[i*2] = aq1_otherChild.measure()
						regOtherChild[i*2+1] = aq2_otherChild.measure()
					to_print = "App {}: nbsd of {} --> i, b1, b2: {}, {}, {}".format(self.node.name, sender, i, int(regSender[i*2]), int(regSender[i*2+1]))
					print(to_print)
					to_print = "App {}: nbsd of {} --> i, b1, b2: {}, {}, {}".format(self.node.name, otherChild, i, int(regOtherChild[i*2]), int(regOtherChild[i*2+1]))
					print(to_print)
					i = i+1
				# Calculate the new global state from the average of the local states of the two child nodes
				avgIntLocalStates = int((int(regSender.to01(),2) + int(regOtherChild.to01(),2))/2)
				avgBitLocalStates = bin(avgIntLocalStates)[2:].zfill(self.d)
				avgBitLocalStatesList = [int(i) for i in str(avgBitLocalStates)]
				i = 0
				while i < self.d:
					self.regVGlobal[i] = avgBitLocalStatesList[i]
					self.regVLocal[i] = avgBitLocalStatesList[i]
					i = i+1
				# Print the new v(t) 
				print("New regVGlobal of {}: {}".format(self.node.name, self.regVGlobal))
				print("New regVLocal of {}: {}".format(self.node.name, self.regVLocal))
				time.sleep(3)		
				
				# Start parentStep3 and parentStep4 with each child node (first one, then the other)
				# Current child node
				self.state[sender] = 'STEP3'
				self.node.sendClassical(sender, str.encode(self.myself+":step3")) # wake up sender to STEP3
				parentStep3(self.node, sender, self.regVGlobal, reg1, reg2, self.d, self.indexes[sender], self.excQubits)
				self.state[sender] = 'STEP4'
				parentStep4(self.node, sender, reg1, reg2, self.d, self.excQubits)
				self.state[sender] = 'WAIT'
				time.sleep(2)
				
				# Other child node
				self.state[otherChild] = 'STEP3'
				self.node.sendClassical(otherChild, str.encode(self.myself+":step3")) # wake up other child to STEP3
				parentStep3(self.node, otherChild, self.regVGlobal, reg1, reg2, self.d, self.indexes[otherChild], self.excQubits)
				self.state[otherChild] = 'STEP4'
				parentStep4(self.node, otherChild, reg1, reg2, self.d, self.excQubits)
				self.state[otherChild] = 'WAIT'				
				
				# Check if the threshold has been exceeded
				if (int(self.regVGlobal.to01(),2) > int(self.t,2)):
					if (self.myid == 0):
						print("*** G12 in the root node has exceeded the threshold: timestamp saved. ***")
						# Update log file and reset the counter of the qubits exchanged
						append_write = 'w'
						if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
							append_write = 'a' # append if already exists
						with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
							file.write(str(datetime.datetime.now())+"_"+self.node.name+"_G12"
									   +"_S:"+str(self.excQubits['sent'])+"_R:"+str(self.excQubits['received'])+"\n")
							self.excQubits['sent'] = 0
							self.excQubits['received'] = 0
					else:
						print("Parent {}: threshold has been exceeded.".format(self.node.name))
						# Update log file and reset the counter of the qubits exchanged
						append_write = 'w'
						if (os.path.isfile(os.path.join('log', self.node.name+'.txt'))):
							append_write = 'a' # append if already exists
						with open(os.path.join('log', self.node.name+'.txt'), append_write) as file:
							file.write(str(datetime.datetime.now())+"_"+self.node.name+"_G"+str(self.myid*2+1)+str(self.myid*2+2)
									   +"_S:"+str(self.excQubits['sent'])+"_R:"+str(self.excQubits['received'])+"\n")
							self.excQubits['sent'] = 0
							self.excQubits['received'] = 0
					
					# Notify the end of the protocol to the child nodes
					self.node.sendClassical(sender, str.encode(self.node.name+":protocol_terminated"))
					self.node.sendClassical(otherChild, str.encode(self.node.name+":protocol_terminated"))
					if (self.myid != 0):
						self.pendingViolation = 1
					else:
						self.busy = 0
				else:
					# Threshold not exceeded
					# Notify the end of the protocol to the child nodes
					self.node.sendClassical(sender, str.encode(self.node.name+":protocol_terminated"))
					self.node.sendClassical(otherChild, str.encode(self.node.name+":protocol_terminated"))
					self.busy = 0
					

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
	d = 4
	# Number of nodes
	n = 7
	# Threshold
	t = '1000'
	qgmnode = QGMNode(myid, d, p, n, t)
	print(qgmnode.identifiers)
		
		
##############################		
main()