
from bitarray import bitarray
from random import *
from time import sleep
from threading import Thread
import sys

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

	def __init__(self, myid, d):
		self.myid = myid
		self.myself = 'node'+str(myid)
		self.d = d
		self.p = 0.8
		self.indexes = {}
		# Create bit register for global state
		self.regVLocal = bitarray(d)
		self.regVGlobal = bitarray(d)
		self.identifiers = {'parent':'unknown', 'leftChild':'unknown', 'rightChild':'unknown'}
		self.state = {}
		if (myid != 0):
			# compute parent id
			idp = 0
			if (myid%2 == 0):
				idp = int((myid - 2)/2)
			elif (myid%2 == 1):
				idp = int((myid - 1)/2)	
			self.identifiers['parent'] = 'node'+str(idp)
			self.state[self.identifiers['parent']] = 'READY'
		else:
			self.identifiers['parent'] = 'null'	
		self.identifiers['leftChild'] = 'node'+str(myid*2+1)
		self.identifiers['rightChild'] = 'node'+str(myid*2+2)
		self.indexes[self.identifiers['parent']] = []
		self.indexes[self.identifiers['leftChild']] = []
		self.indexes[self.identifiers['rightChild']] = []
		self.state = {}
		self.state[self.identifiers['leftChild']] = 'READY'
		self.state[self.identifiers['rightChild']] = 'READY'
		# Create qubit registers for EPR pairs
		self.regA = {}
		self.regA[self.identifiers['leftChild']] = [] # for own qubits entangled with those of left child
		self.regA[self.identifiers['rightChild']] = [] # for own qubits entangled with those of right child
		self.regAB = {}
		self.regAB[self.identifiers['leftChild']] = []  # for qubits coming from left child
		self.regAB[self.identifiers['rightChild']] = []  # for qubits coming from right child
		self.regB = {}	
		self.regBA = {}
		# Create qubit registers for EPR pairs shared with parent
		self.regB[self.identifiers['parent']] = []
		self.regBA[self.identifiers['parent']] = []
		# Initialize the CQC connection
		self.node = CQCConnection(self.myself)
		# if node is not root, detach an elaboration thread
		if (myid != 0):
			self.startLocalProcessing()
		# start the listening loop	
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

		## Child setup	
		# Create bit registers for local state
		i = 0
		while i < self.d:	
			self.regVLocal[i] = 0
			i = i+1

		wt = random()*10 # FIXME dovrebbe essere il padre a iniziare STEP1 in modo da annullare la concorrenza 
		time.sleep(wt)
				
		# send classical message to parent
		self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself))	
		self.state[self.identifiers['parent']] = 'STEP1'
		childStep1(self.node, self.identifiers['parent'], self.regB, self.regBA, self.d)
		self.state[self.identifiers['parent']] = 'PROC'	
		
		# main loop
		while True:
			to_print = "## [localProcessing] Child {}: current state is {}".format(self.node.name, self.state[self.identifiers['parent']])
			print(to_print)
			if (self.state[self.identifiers['parent']] == 'PROC'):
				wt = random()*60
				time.sleep(wt)
				if (self.state[self.identifiers['parent']] == 'PROC'):	 # re-check
					# randomly change some bits in the local state register
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
					to_print = "## PROC ## Child {}: new local state {}".format(self.node.name, self.regVLocal)
					print(to_print)	
	
					if flag == 1:
						# notify parent about local violation 
						self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself))
						# update the Bell pairs and send changed qubits to parent
						self.state[self.identifiers['parent']] = 'STEP2'					
						del self.indexes[self.identifiers['parent']][:] # perform some cleaning
						childStep2(self.node, self.identifiers['parent'], self.regVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']])
					
			elif (self.state[self.identifiers['parent']] != 'PROC'):
				wt = 10
				time.sleep(wt)


	##############################################
	#
	#  listening loop (starting message handling in a separate thread)
	#
	def listen(self):
		## Parent setup	
		i = 0
		while i < self.d:
			self.regVGlobal[i] = 0	
			i = i+1
		
		while True:
			data = self.node.recvClassical()			sender = data.decode()
			to_print = "App {}: received message from: {}".format(self.node.name, sender)
			print(to_print)
			# detach a thread to handle the communication
			if (sender == self.identifiers['parent']):
				tComm = Thread(target=self.commHandler, args=(sender, self.regB, self.regBA))
				#self.commHandler(sender, self.regB, self.regBA)
			else:
				tComm = Thread(target=self.commHandler, args=(sender, self.regA, self.regAB))
				#self.commHandler(sender, self.regB, self.regAB)
			tComm.start()

		
	###################################
	#
	#  handler for messages coming from any node
	#
	def commHandler(self, sender, reg1, reg2):
		to_print = "commHandler - message sender is: {}".format(sender)
		print(to_print)
	
		# child actions
		if (sender == self.identifiers['parent']):
			if (self.state[sender] == 'PROC'):
				self.state[sender] = 'WAIT'
				to_print = "#### Child {}: forced to {} by {}".format(self.node.name, self.state[sender], sender)
				print(to_print)
			elif (self.state[sender] == 'WAIT'):	
				# update the Bell pairs and send changed qubits to parent
				self.state[sender] = 'STEP2'
				del self.indexes[self.identifiers['parent']][:] # perform some cleaning
				childStep2(self.node, self.identifiers['parent'], self.regVLocal, self.regB, self.regBA, self.d, self.indexes[self.identifiers['parent']])
			elif (self.state[sender] == 'STEP2'):
				self.state[sender] = 'STEP3'
				childStep3(self.node, sender, reg1, reg2, self.d, self.indexes[self.identifiers['parent']])
				self.state[sender] = 'STEP4'
				childStep4(self.node, sender, self.regVGlobal, reg1, reg2, self.d)	
			elif (self.state[sender] == 'STEP4'):
				to_print = "#### Child {}: end protocol notified by {}".format(self.node.name, sender)
				print(to_print)
				self.state[sender] = 'PROC'
				
		# parent actions
		else:
			otherChild = 'temp'
			if (sender == self.identifiers['leftChild']):
				otherChild = self.identifiers['rightChild']
			else:
				otherChild = self.identifiers['leftChild']	 
			if (self.state[sender] == 'READY'):
				self.state[sender] = 'STEP1'
				parentStep1(self.node, sender, reg1, reg2, self.d)
				self.state[sender] = 'WAIT'
			elif (self.state[sender] == 'WAIT'):
				# send classical mess to force other child to WAIT (assuming it is in state PROC)
				self.node.sendClassical(otherChild, str.encode(self.myself))				
				#perform parentStep2 with child that notified a violation
				self.state[sender] = 'STEP2'
				del self.indexes[sender][:] # perform some cleaning
				parentStep2(self.node, sender, reg2, self.d, self.indexes[sender])
				
				# send classical mess to force other child to STEP2 (assuming it is in state WAIT)
				self.node.sendClassical(otherChild, str.encode(self.myself))
				# perform parentStep2 with other child
				self.state[otherChild] = 'STEP2'
				del self.indexes[otherChild][:] # perform some cleaning
				parentStep2(self.node, otherChild, reg2, self.d, self.indexes[otherChild])
								
				# update regVGlobal
				time.sleep(2)
				to_print = "## 3 ## Parent {}: updating regVGlobal".format(self.node.name)
				print(to_print)	
				# perform Bell state discrimination by nondestructive measurement 
				# on the local Bell pairs (whose indexes have been saved)
				print(len(self.indexes[sender]))
				i = 0
				while i < len(self.indexes[sender]):
					aq1 = qubit(self.node)
					aq2 = qubit(self.node)
					nondestructiveBellStateDiscrimination(reg1[sender][i], reg2[sender][i], aq1, aq2)
					b1 = aq1.measure()
					self.regVGlobal[i] = b1; # FIXME regVGlobal should contain the average of all children's reports
					b2 = aq2.measure()
					self.regVGlobal[i+1] = b2; # FIXME regVGlobal should contain the average of all children's reports
					to_print = "App {}: nbsd i, b1, b2: {}, {}, {}".format(self.node.name,i,b1,b2)
					print(to_print)
					i = i+1	
				# print the new v(t) 
				print(self.regVGlobal)
				time.sleep(3)		
				
				# perform parentStep3 and parentStep4 with each child (first one, then the other)
				self.state[sender] = 'STEP3'
				self.node.sendClassical(sender, str.encode(self.myself)) # wake up sender to STEP3
				parentStep3(self.node, sender, self.regVGlobal, reg1, reg2, self.d, self.indexes[sender])
				self.state[sender] = 'STEP4'
				parentStep4(self.node, sender, reg1, reg2, self.d)
				self.state[sender] = 'WAIT'
				time.sleep(2)	
				self.state[otherChild] = 'STEP3'
				self.node.sendClassical(otherChild, str.encode(self.myself)) # wake up other child to STEP3
				parentStep3(self.node, otherChild, self.regVGlobal, reg1, reg2, self.d, self.indexes[otherChild])
				self.state[otherChild] = 'STEP4'
				parentStep4(self.node, otherChild, reg1, reg2, self.d)
				self.state[otherChild] = 'WAIT'				
				
				# notify end protocol to children
				self.node.sendClassical(sender, str.encode(self.node.name))
				self.node.sendClassical(otherChild, str.encode(self.node.name))
					

##############################
#
# main   
#
def main():

	print('Number of arguments:', len(sys.argv), 'arguments.')
	print('Argument List:', str(sys.argv))

	myid = int(sys.argv[1])
	qgmnode = QGMNode(myid, 4)
	print(qgmnode.identifiers)
		
		
##############################		
main()