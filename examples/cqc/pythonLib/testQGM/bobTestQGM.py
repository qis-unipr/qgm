#
# Copyright (c) 2018, Michele Amoretti and Stefano Carretta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#    This product includes software developed by Michele Amoretti, University of Parma.
# 4. Neither the name of the University of Parma organization nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from SimulaQron.general.hostConfig import *
from SimulaQron.cqc.backend.cqcHeader import *
from SimulaQron.cqc.pythonLib.cqc import *

from bitarray import bitarray
from random import *
from time import sleep

from utils import *

##############################
#
# main
#
def main():

	# Initialize the connection
	Bob=CQCConnection("Bob")

	# Local qubit change probability
	p = 0.8  
	
	# Size of monitored data
	d = 4

	# Create bit registers for global and local states
	to_print="App {}: Create bit registers".format(Bob.name)
	print(to_print)
	regVGlobal = bitarray(d)
	regVLocal = bitarray(d)	
	i = 0
	while i < d:
		regVGlobal[i] = 0	
		regVLocal[i] = 0
		i = i+1
	#to_print = "App {}: regVGlobal = ".format(Bob.name)
	#print(to_print) 
	#print(regVGlobal)	
	#to_print = "App {}: regVLocal = ".format(Bob.name)
	#print(to_print) 
	#print(regVLocal)
	
	# Create qubit register for Bob's qubits of EPR pairs shared with Alice
	regB = []
	regBA = []


	### QGM STEP 1
	to_print = "##### App {} - QGM STEP 1 #####".format(Bob.name)
	print(to_print)

	# Receive qubits
	i = 0
	while i < d/2:
		regB.append(Bob.recvEPR())
		regBA.append(qubit(Bob)) # this is a code trick to make the second register grow like the first one
		i = i+1


	### QGM STEP 2
	
	# randomly change some bits in the local state register
	to_print = "##### App {} - QGM STEP 2 #####".format(Bob.name)
	print(to_print)
	i = 0
	flag = 0
	while i < d:
		r = random()
		if r < p:
			if regVLocal[i] == 1:
				regVLocal[i] = 0
			elif regVLocal[i] == 0:
				regVLocal[i] = 1
			flag = 1
		i = i+1
	print(regVLocal)
	
	if flag == 1:
		# notify Alice about local violation 
		Bob.sendClassical("Alice", "1")
		# change the corresponding Bell pairs and send changed qubits to Alice
		sleep(0.5)
		indexes = []
		i = 0
		while  i < d/2:
			if ((regVLocal[i*2] == 0) and (regVLocal[i*2+1] == 1)):
				# turn Beta00 to Beta01
				regB[i].X()
				Bob.sendQubit(regB[i],"Alice")
				indexes.append(i)
			elif ((regVLocal[i*2] == 1) and (regVLocal[i*2+1] == 0)):
				# turn Beta00 to Beta10
				regB[i].Z()
				Bob.sendQubit(regB[i],"Alice") 	
				indexes.append(i)
			elif ((regVLocal[i*2] == 1) and (regVLocal[i*2+1] == 1)):
				# turn Beta00 to Beta11
				regB[i].Z()
				regB[i].X()
				Bob.sendQubit(regB[i],"Alice")	
				indexes.append(i)
			else:	
				print("send nothing")
			i = i+1	
			sleep(1)
	else:
		Bob.sendClassical("Alice", "0") # this is a trick to unblock Alice
	
	sleep(2)
	

	### QGM STEP 3
	
	# wait for notification about updated qubits ready for being transmitted by Alice
	to_print = "##### App {} - QGM STEP 3 #####".format(Bob.name)
	print(to_print)
	data = Bob.recvClassical() 	message = list(data)	b = message[0]
	to_print = "App {}: received notification from Alice: {}".format(Bob.name,b)
	print(to_print)
	if b == 1:
		# receive all the updated Bell pairs from Alice
		i = 0
		while  i < d/2:
			if (i in indexes):
				to_print = "App {}: i in indexes: {}".format(Bob.name,i)
				print(to_print)
				try:
					regB[i] = Bob.recvEPR()
					to_print = "App {} received his half of the {}-th Bell pair".format(Bob.name,i)
					print(to_print)
				except CQCTimeoutError:
					to_print = "App {} did not receive his half of the {}-th Bell pair".format(Bob.name,i)
					print(to_print)		
				sleep(2)						
				try:
					regBA[i]=Bob.recvQubit()
					to_print = "App {} received Alice's half of the {}-th Bell pair".format(Bob.name,i)
					print(to_print)
				except CQCTimeoutError:
					to_print = "App {} did not receive Alice's half of the {}-th Bell pair".format(Bob.name,i)
					print(to_print)
				sleep(2)		
			else:
				to_print = "App {}: i not in indexes: {}".format(Bob.name,i)
				print(to_print)
				try:
					regBA[i]=Bob.recvQubit()
					to_print = "App {} received regBA[{}]".format(Bob.name,i)
					print(to_print)
				except CQCTimeoutError:
					to_print = "App {} did not receive regBA[{}]".format(Bob.name,i)
					print(to_print)
				sleep(2)				
			i = i+1	
	
	
	### QGM STEP 4
	
	# At this pont, Bob owns all qubits grouped as EPR pairs regB[i]regBA[i]
	to_print = "##### App {} - QGM STEP 4 #####".format(Bob.name)
	print(to_print)
	
	# update regVGlobal[]
	i = 0
	while  i < d/2:
		# perform Bell state discrimination by nondestructive measurement 
		# on regB[i]regBA[i] and update regVGlobal[] accordingly
		aq1 = qubit(Bob)
		aq2 = qubit(Bob)
		nondestructiveBellStateDiscrimination( regBA[i], regB[i], aq1, aq2 )
		b1 = aq1.measure()
		b2 = aq2.measure()
		to_print = "App {}: nbsd i, b1, b2: {}, {}, {}".format(Bob.name,i,b1,b2)
		print(to_print)
		regVGlobal[i*2] = b1
		regVGlobal[i*2+1] = b2
		i = i+1
	
	# reinitialize Bell pairs to the 00 state
	i = 0
	while  i < d/2:
		try:
			regB[i].measure() # cleaning
			regBA[i].measure() # cleaning
		except QubitNotActiveError:
			pass	
		regB[i] = Bob.createEPR("Alice")
		i = i+1
		sleep(2)
	
	sleep(3)
	
	
	# perform some cleaning
	to_print = "##### App {} final cleaning #####".format(Bob.name)
	print(to_print)
	i = 0
	while i < d/2:
		try:
			regB[i].measure()
			regBA[i].measure()
		except QubitNotActiveError:
			pass	
		i = i+1	
	
	# Stop the connection
	Bob.close()

##############################
main()

