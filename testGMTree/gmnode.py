
from bitarray import bitarray
from random import *
from time import sleep
from threading import Thread
from subprocess import call
import sys, os, re, datetime

from cqc.pythonLib import *


##############################
#
# QGMNode class derived from CQCConnection, with reg* attributes
#

class GMNode():

	def __init__(self, myid, d, p, n, t, l):
		self.myid = myid
		self.myself = 'node'+str(myid)
		self.d = d
		self.p = p
		self.n = n
		self.t = t
		self.l = l

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
		# Flag to determine if the parent node has received a response after his 'get local state' message
		self.localStateReceived = 0
		# Flag to determine the number of times the root node has exceeded the threshold
		self.overrunNumberChild = 0
		self.overrunNumberParent = 0
		self.overrunNumberFromChilds = 0

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
		self.excBits = {'sent':0, 'received':0}

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
			if not os.path.exists("log2"):
				os.makedirs("log2")
			if not os.path.exists("G12"):
				os.makedirs("G12")

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

		# Set the two child nodes in the READY state
		self.state = {}
		self.state[self.identifiers['leftChild']] = 'READY'
		self.state[self.identifiers['rightChild']] = 'READY'

		# Bit registers for child's local state
		self.regDeltaVLocalChild = {}
		self.regDeltaVLocalChild[self.identifiers['leftChild']] = bitarray(d)
		self.regDeltaVLocalChild[self.identifiers['rightChild']] = bitarray(d)

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

		# Initialize to 0 the bit registers for the local state
		i = 0
		while i < self.d:
			self.regVLocal[i] = 0
			self.regDeltaVLocal[i] = 0
			i = i+1

		self.state[self.identifiers['leftChild']] = 'WAIT'
		self.state[self.identifiers['rightChild']] = 'WAIT'
		self.state[self.identifiers['parent']] = 'PROC'

		time.sleep(2)

		# Main loop
		while True:
			to_print = "## [localProcessing] Child {}: current state is {}".format(self.node.name, self.state[self.identifiers['parent']])
			print(to_print)

			# If the parent node is in the PROC state, sleep by a random value, double-check that it is still in the PROC state
			# and finally randomly changes some bits of the local state register
			if (self.state[self.identifiers['parent']] == 'PROC'):
				if (self.pendingViolation == 0):
					wt = randint(5,11)*2
					time.sleep(wt)
				else:
					wt = randint(2,5)
					time.sleep(wt)
				if (self.state[self.identifiers['parent']] == 'PROC'):	 # re-check
					# Check if there is a previous local violation not yet notified
					# If there are none, it normally proceeds, otherwise it manages that pendant
					if (self.pendingViolation == 0 and self.leafNode == 1):
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
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":only_parent_free"))
							waitLoop = True
							while waitLoop:
								if (self.parentAnsw == 1 or self.parentAnsw == 2):
									waitLoop = False
							# Check if it can notify the local violation
							if (self.parentAnsw == 2):
								to_print = "## PROC ## Child {}: new local state after local violation: {}".format(self.node.name, self.new_localStateBit)
								print(to_print)
								# Notify the parent node of the local violation by sending it a classic message
								self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation"))
								self.state[self.identifiers['parent']] = 'WAIT'
							else:
								self.pendingViolation = 1
								to_print = "## PROC ## Child {}: local violation occurred but cannot notify now: {}".format(self.node.name, self.new_localStateBit)
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
							to_print = "## PROC ## Child {}: handling the pending local violation occurred before: {}".format(self.node.name, self.new_localStateBit)
							print(to_print)
							# Notify the parent node of the local violation by sending it a classic message
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation"))
							self.state[self.identifiers['parent']] = 'WAIT'
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
							if (self.notifyFlag == 1 or self.pendingViolation == 0):
								waitLoop = False
							else:
								time.sleep(6)
								if (self.notifyFlag == 0 and self.pendingViolation == 1):
									self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":free_parent_req"))
						if (self.notifyFlag):
							self.notifyFlag = 0
							to_print = "## PROC ## Child {}: threshold exceeded synchronization with the parent".format(self.node.name)
							print(to_print)
							# Notify the parent node of the local violation by sending it a classic message
							self.node.sendClassical(self.identifiers['parent'], str.encode(self.myself+":child_violation"))
							self.state[self.identifiers['parent']] = 'WAIT'
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

		if (self.myid == 0):
			self.state[self.identifiers['leftChild']] = 'WAIT'
			self.state[self.identifiers['rightChild']] = 'WAIT'

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
			if (msg == "free_parent_req"):
				if (self.busy):
					self.node.sendClassical(sender, str.encode(self.myself+":parent_not_free"))
				else:
					self.busy = 1
					self.node.sendClassical(otherChild, str.encode(self.myself+":free_child_req"))
			elif (msg == "free_child_req"):
				if (self.busy == 1 and self.pendingViolation == 0):
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
			elif (msg == "release_otherChild"):
				self.node.sendClassical(otherChild, str.encode(self.myself+":release"))
			elif (msg == "release"):
				self.busy = 0
				self.pendingViolation = 0
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
			elif (msg == "ls"):
				variation = content[2]
				self.sign2[sender] = content[3]
				self.overrunNumberFromChilds += int(content[4])
				i = 0
				while i < self.d:
					self.regDeltaVLocalChild[sender][i] = int(variation[i])
					i = i+1
				self.localStateReceived = 1
			elif (msg == "protocol_terminated"):
				newGlobalState = content[2]
				i = 0
				while i < self.d:
					self.regVGlobal[i] = int(newGlobalState[i])
					self.regVLocal[i] = int(newGlobalState[i])
					i = i+1
				self.excBits['received'] += self.d
				tComm = Thread(target=self.commHandler, args=(sender, self.regDeltaVLocalChild))
				tComm.start()
			else:
				# Start a new thread to handle the communication
				tComm = Thread(target=self.commHandler, args=(sender, self.regDeltaVLocalChild))
				tComm.start()


	###################################
	#
	#  handler for messages coming from any node
	#
	def commHandler(self, sender, regDeltaVLocalChild):

		### Actions as child node ###
		if (sender == self.identifiers['parent']):
			if (self.state[sender] == 'PROC'):
				self.busy = 1
				self.state[sender] = 'WAIT'
				to_print = "#### Child {}: forced to {} by {}".format(self.node.name, self.state[sender], sender)
				print(to_print)
			elif (self.state[sender] == 'WAIT'):
				self.node.sendClassical(sender, str.encode(self.myself+":ls:"+self.regDeltaVLocal.to01()+":"+self.sign+":"+str(self.overrunNumberParent)))
				self.excBits['sent'] += self.d
				self.state[sender] = 'WAIT_END'
			elif (self.state[sender] == 'WAIT_END'):
				self.overrunNumberChild += 1
				to_print = "#### Child {}: end protocol notified by {}".format(self.node.name, sender)
				print(to_print)
				if (self.leafNode):
					# Update log file and reset the counter of bits exchanged only for the leaf nodes
					append_write = 'w'
					if (os.path.isfile(os.path.join('log2', self.node.name+'.txt'))):
						append_write = 'a' # append if already exists
					with open(os.path.join('log2', self.node.name+'.txt'), append_write) as file:
						file.write(str(datetime.datetime.now())+"_"+self.node.name+"_LV_S:"+str(self.excBits['sent'])+"_R:"+str(self.excBits['received'])+"\n")
					self.excBits['sent'] = 0
					self.excBits['received'] = 0
				else:
					# Update log file and reset the counter of the bits exchanged only for non-leaf nodes
					append_write = 'w'
					if (os.path.isfile(os.path.join('log2', self.node.name+'.txt'))):
						append_write = 'a' # append if already exists
					with open(os.path.join('log2', self.node.name+'.txt'), append_write) as file:
						file.write(str(datetime.datetime.now())+"_"+self.node.name+"_G"+str(self.myid*2+1)+str(self.myid*2+2)
								   +"_S:"+str(self.excBits['sent'])+"_R:"+str(self.excBits['received'])+"\n")
					self.excBits['sent'] = 0
					self.excBits['received'] = 0
				if (self.otherChildPending):
					self.node.sendClassical(sender, str.encode(self.myself+":release_otherChild"))
					self.otherChildPending = 0
				if (self.pendingViolation == 0):
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

				# Send a message to the other child node to force him to wait
				self.node.sendClassical(otherChild, str.encode(self.myself+":wait"))

				# Send a message to the sender child node to get his local state
				self.node.sendClassical(sender, str.encode(self.myself+":get_localstate"))

				# Wait for the response from the other child node
				waitLoop = True
				while waitLoop:
					if (self.localStateReceived):
						self.localStateReceived = 0
						waitLoop = False

				self.excBits['received'] += self.d

				to_print = "Parent {}: received local variation from {}: {}".format(self.node.name, sender, regDeltaVLocalChild[sender])
				print(to_print)

				# Send a message to the other child node to get his local state
				self.node.sendClassical(otherChild, str.encode(self.myself+":get_localstate"))

				# Wait for the response from the other child node
				waitLoop = True
				while waitLoop:
					if (self.localStateReceived):
						self.localStateReceived = 0
						waitLoop = False

				self.excBits['received'] += self.d

				to_print = "Parent {}: received local variation from {}: {}".format(self.node.name, otherChild, regDeltaVLocalChild[otherChild])
				print(to_print)

				# Calculate the new global state from the average of the local states of the two child nodes
				avgIntLocalStates = 0
				state = int(self.regVLocal.to01(), 2)
				variationSender = int(regDeltaVLocalChild[sender].to01(), 2)
				if self.sign2[sender] == "+":
					avgIntLocalStates += (state + variationSender)
				elif self.sign2[sender] == "-":
					avgIntLocalStates += (state - variationSender)
				else:
					avgIntLocalStates += state
				variationOtherChild = int(regDeltaVLocalChild[otherChild].to01(), 2)
				if self.sign2[otherChild] == "+":
					avgIntLocalStates += (state + variationOtherChild)
				elif self.sign2[otherChild] == "-":
					avgIntLocalStates += (state - variationOtherChild)
				else:
					avgIntLocalStates += state
				avgIntLocalStates /= 2
				avgBitLocalStates = bin(int(avgIntLocalStates))[2:].zfill(self.d)
				avgBitLocalStatesList = [int(i) for i in str(avgBitLocalStates)]
				i = 0
				while i < self.d:
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
				print("New regVLocal of {}: {}".format(self.node.name, self.regVLocal))
				time.sleep(1)

				if (self.myid == 0):
					# Log G12
					append_write = 'w'
					if (os.path.isfile(os.path.join('G12', 'G12.txt'))):
						append_write = 'a' # append if already exists
					with open(os.path.join('G12', 'G12.txt'), append_write) as file:
						file.write(str(datetime.datetime.now())+"_"+str(int(self.regVLocal.to01(), 2))+"\n")

				self.overrunNumberParent += 1

				# Calculate the new variation to comunicate to the parent node
				new_variation = int(self.regVLocal.to01(), 2) - int(self.regVGlobal.to01(), 2)
				if new_variation < 0:
					self.sign = "-"
				else:
					self.sign = "+"
				new_variation_bit = str(bin(abs(new_variation))[2:].zfill(self.d))
				i = 0
				while i < self.d:
					self.regDeltaVLocal[i] = int(new_variation_bit[i])
					i = i+1

				tot_step234 = self.overrunNumberParent + self.overrunNumberChild + self.overrunNumberFromChilds

				# Check if the threshold has been exceeded
				if (int(self.regVLocal.to01(),2) > int(self.t,2)):
					# Notify the end of the protocol to the child nodes with the new global state
					self.node.sendClassical(sender, str.encode(self.node.name+":protocol_terminated:"+self.regVLocal.to01()))
					self.node.sendClassical(otherChild, str.encode(self.node.name+":protocol_terminated:"+self.regVLocal.to01()))
					self.excBits['sent'] += self.d*2
					time.sleep(1)

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
							file.write(str(datetime.datetime.now())+"_"+self.node.name+"_G"+str(self.myid*2+1)+str(self.myid*2+2)+"_S:"+
									   str(self.excBits['sent'])+"_R:"+str(self.excBits['received'])+"\n")
						self.excBits['sent'] = 0
						self.excBits['received'] = 0
					else:
						print("Parent {}: threshold has been exceeded.".format(self.node.name))

					if tot_step234 >= self.l:
						print(tot_step234)
						call(["killall", "python3"])

					if (self.myid != 0):
						self.pendingViolation = 1
					else:
						self.busy = 0
				else:
					# Threshold not exceeded
					# Notify the end of the protocol to the child nodes with the new global state
					self.node.sendClassical(sender, str.encode(self.node.name+":protocol_terminated:"+self.regVLocal.to01()))
					self.node.sendClassical(otherChild, str.encode(self.node.name+":protocol_terminated:"+self.regVLocal.to01()))
					self.excBits['sent'] += self.d*2
					self.busy = 0

					if tot_step234 >= self.l:
						print(tot_step234)
						call(["killall", "python3"])

				self.overrunNumberFromChilds = 0


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
	gmnode = GMNode(myid, d, p, n, t, l)
	print(gmnode.identifiers)


##############################
main()
