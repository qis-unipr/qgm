
from SimulaQron.general.hostConfig import *
from SimulaQron.cqc.backend.cqcHeader import *
from SimulaQron.cqc.pythonLib.cqc import *

from bitarray import bitarray
from random import random
import time

from utils import *


###################################
#
#  Child Step 1
#
def childStep1(node, sender, regB, regBA, d, excQubits):

	to_print = "## 1 ## Child {}: performing STEP1 with {}".format(node.name, sender)
	print(to_print)
	# Receive qubits
	i = 0
	while i < d/2:
		try:	
			regB[sender].append(node.recvEPR())
			excQubits['received'] += 1
			regBA[sender].append(qubit(node)) # this is a code trick to make the second register grow like the first one
		except CQCTimeoutError:
			print("Child did not receive half EPR")	
		time.sleep(2)	
		i = i+1
	#print(len(regB[sender]))
	#print(len(regBA[sender])	)	
	
	
###################################
#
#  Parent Step 1
#
def parentStep1(node, sender, regA, regAB, d, excQubits):
	to_print = "## 1 ## Parent {}: performing STEP1 with {}".format(node.name, sender)
	print(to_print)
	time.sleep(0.5)
	i = 0
	while i < d/2:
		regA[sender].append(node.createEPR(sender))
		excQubits['sent'] += 1
		regAB[sender].append(qubit(node)) # this is a code trick to make the second register grow like the first one
		time.sleep(2)	
		i = i+1
	#print(len(regA[sender]))
	#print(len(regAB[sender])	)	
	

###################################
#
#  Child Step 2
#
def childStep2(node, sender, regVLocal, regB, regBA, d, indexes, excQubits):
	to_print = "## 2 ## Child {}: performing STEP2 with {}".format(node.name, sender)
	print(to_print)
	time.sleep(0.5)
	i = 0
	while  i < d/2:
		if ((regVLocal[i*2] == 0) and (regVLocal[i*2+1] == 1)):
			# turn Beta00 to Beta01
			regB[sender][i].X()
			node.sendQubit(regB[sender][i], sender)
			indexes.append(i)
			excQubits['sent'] += 1
		elif ((regVLocal[i*2] == 1) and (regVLocal[i*2+1] == 0)):
			# turn Beta00 to Beta10
			regB[sender][i].Z()
			node.sendQubit(regB[sender][i], sender) 	
			indexes.append(i)
			excQubits['sent'] += 1
		elif ((regVLocal[i*2] == 1) and (regVLocal[i*2+1] == 1)):
			# turn Beta00 to Beta11
			regB[sender][i].Z()
			regB[sender][i].X()
			node.sendQubit(regB[sender][i], sender)	
			indexes.append(i)
			excQubits['sent'] += 1
		else:
			to_print = "App node {}: send nothing to: {}".format(node.name, sender)
			print(to_print)
		time.sleep(2)	
		i = i+1	

	
###################################
#
#  Parent Step 2
#
def parentStep2(node, sender, regAB, d, indexes, excQubits):
	to_print = "## 2 ## Parent {}: performing STEP2 with {}".format(node.name, sender)
	print(to_print)
	#print("Parent Step 2 - regAB size: " + str(len(regAB[sender])))
	# get changed qubits from child 
	i = 0
	while  i < d/2:
		#print(i)
		try:
			regAB[sender][i] = node.recvQubit()
			indexes.append(i)
			excQubits['received'] += 1
			print("Parent {} received a qubit from {}".format(node.name, sender))
		except CQCTimeoutError:
			print("Parent {} did not receive a qubit from {}".format(node.name, sender))
		time.sleep(2)		
		i = i+1	
	#print(len(indexes))	

###################################
#
#  Child Step 3
#
def childStep3(node, sender, regB, regBA, d, indexes, excQubits):
	to_print = "## 3 ## Child {}: performing STEP3 with {}".format(node.name, sender)
	print(to_print)
	# receive all the updated Bell pairs from parent
	i = 0
	while  i < d/2:
		if (i in indexes):
			to_print = "App {}: i in indexes: {}".format(node.name,i)
			print(to_print)
			try:
				regB[sender][i].measure() # cleaning
				regBA[sender][i].measure() # cleaning
			except QubitNotActiveError:
				pass
			try:
				regB[sender][i] = node.recvEPR()
				excQubits['received'] += 1
				to_print = "App {} received his half of the {}-th Bell pair".format(node.name,i)
				print(to_print)
			except CQCTimeoutError:
				to_print = "App {} did not receive his half of the {}-th Bell pair".format(node.name,i)
				print(to_print)		
			time.sleep(2)						
			try:
				regBA[sender][i] = node.recvQubit()
				excQubits['received'] += 1
				to_print = "App {} received parent's half of the {}-th Bell pair".format(node.name,i)
				print(to_print)
			except CQCTimeoutError:
				to_print = "App {} did not receive parent's half of the {}-th Bell pair".format(node.name,i)
				print(to_print)
			time.sleep(2)		
		else:
			to_print = "App {}: i not in indexes: {}".format(node.name,i)
			print(to_print)
			try:
				regBA[sender][i] = node.recvQubit()
				excQubits['received'] += 1
				to_print = "App {} received regBA[{}]".format(node.name,i)
				print(to_print)
			except CQCTimeoutError:
				to_print = "App {} did not receive regBA[{}]".format(node.name,i)
				print(to_print)
			time.sleep(2)				
		i = i+1
	
	
###################################
#
#  Parent Step 3
#
def parentStep3(node, sender, regVGlobal, regA, regAB, d, indexes, excQubits):
			
	# update the shared Bell pairs (only those that must change) and send them to the child
	time.sleep(0.5)
	i = 0
	while  i < d/2:
		# case of Bell pair that is local to the parent, thus != Beta00
		if (i in indexes):
			to_print = "App {}: i in indexes: {}".format(node.name,i)
			print(to_print)
			# replace Bell pair with new one in Beta00 state
			try:
				regA[sender][i].measure() # cleaning
				regAB[sender][i].measure() # cleaning
			except QubitNotActiveError:
				pass	
			regA[sender][i] = node.createEPR(sender)
			excQubits['sent'] += 1
			time.sleep(2)
		# apply gates to regA[i] depending on wanted new state
		if ((regVGlobal[i*2] == 0) and (regVGlobal[i*2+1] == 1)):
			# turn Beta00 to Beta01
			regA[sender][i].X()
		elif ((regVGlobal[i*2] == 1) and (regVGlobal[i*2+1] == 0)):
			# turn Beta00 to Beta10
			regA[sender][i].Z()
		elif ((regVGlobal[i*2] == 1) and (regVGlobal[i*2+1] == 1)):
			# turn Beta00 to Beta11
			regA[sender][i].X()
			regA[sender][i].Z()	
		# send parent's qubit to child
		node.sendQubit(regA[sender][i], sender)
		excQubits['sent'] += 1
		i = i+1	
		time.sleep(2)


###################################
#
#  Child Step 4
#
def childStep4(node, sender, regVGlobal, regB, regBA, d, excQubits):
	to_print = "## 4 ## Child {}: performing STEP4 with {}".format(node.name, sender)
	print(to_print)
	# update regVGlobal[]
	i = 0
	while  i < d/2:
		# perform Bell state discrimination by nondestructive measurement 
		# on regB[i]regBA[i] and update regVGlobal[] accordingly
		aq1 = qubit(node)
		aq2 = qubit(node)
		nondestructiveBellStateDiscrimination( regBA[sender][i], regB[sender][i], aq1, aq2 )
		b1 = aq1.measure()
		b2 = aq2.measure()
		to_print = "App {}: nbsd i, b1, b2: {}, {}, {}".format(node.name,i,b1,b2)
		print(to_print)
		regVGlobal[i*2] = b1
		regVGlobal[i*2+1] = b2
		i = i+1
	
	# reinitialize Bell pairs to the 00 state
	i = 0
	while  i < d/2:
		try:
			regB[sender][i].measure() # cleaning
			regBA[sender][i].measure() # cleaning
		except QubitNotActiveError:
			pass			
		i = i+1	
	#print(len(regB[sender]))
	#print(len(regBA[sender]))
	i = 0
	while  i < d/2:			
		regB[sender][i] = node.createEPR(sender)
		excQubits['sent'] += 1
		regBA[sender][i] = qubit(node)
		i = i+1
	
	
###################################
#
#  Parent Step 4
#
def parentStep4(node, sender, regA, regAB, d, excQubits):
	to_print = "## 4 ## Parent {}: performing STEP4 with {}".format(node.name, sender)
	print(to_print)
	time.sleep(2)
	# get reinitialized qubits from the child
	i = 0
	while i < d/2:
		try:
			regA[sender][i].measure() # cleaning
			regAB[sender][i].measure() # perform some cleaning
		except QubitNotActiveError:
			pass			
		i = i+1		
	#print(len(regA[sender]))
	#print(len(regAB[sender]))		
	i = 0
	while i < d/2:
		try:
			regA[sender][i] = node.recvEPR()
			excQubits['received'] += 1
			to_print = "App {} received its half of the {}-th Bell pair".format(node.name,i)
			print(to_print)
			regAB[sender][i] = qubit(node)
		except CQCTimeoutError:
			to_print = "App {} did not receive its half of the {}-th Bell pair".format(node.name,i)
			print(to_print)				
		i = i+1

