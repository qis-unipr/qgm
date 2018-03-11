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
	Alice=CQCConnection("Alice")
	
	# Local qubit change probability
	q = 0.4
	
	# Size of monitored data
	d = 4

	# Create bit register for global state
	to_print="App {}: Create bit register".format(Alice.name)
	print(to_print)
	regVGlobal = bitarray(d)	
	i = 0
	while i < d:
		regVGlobal[i] = 0	
		i = i+1


	### QGM STEP 1
	
	to_print = "##### App {} - QGM STEP 1 #####".format(Alice.name)
	print(to_print)
	
	# Create qubit registers for EPR pairs
	regA = []
	regAB = []
	i = 0
	while i < d/2:
		regA.append(Alice.createEPR("Bob"))
		regAB.append(qubit(Alice)) # this is a code trick to make the second register grow like the first one
		i = i+1
		
		
	### QGM STEP 2
	
	# wait for notification from Bob about local violation 
	to_print = "##### App {} - QGM STEP 2 #####".format(Alice.name)
	print(to_print)
		
	data = Alice.recvClassical() # TODO: get sender name	message = list(data)	b = message[0]
	to_print = "App {}: received notification from Bob: {}".format(Alice.name,b)
	print(to_print)
	if b == 1:
		indexes = []
		# get changed qubits from Bob 
		i = 0
		while  i < d/2:
			try:
				regAB[i]=Alice.recvQubit()
				indexes.append(i)
				print("Alice received a qubit")
			except CQCTimeoutError:
				print("Alice did not receive a qubit")
			i = i+1
	
	
	### QGM STEP 3
	
	to_print = "##### App {} - QGM STEP 3 #####".format(Alice.name)
	print(to_print)
	
	# perform Bell state discrimination by nondestructive measurement 
	# on the local Bell pairs (whose indexes have been saved)
	i = 0
	while i < len(indexes):
		aq1 = qubit(Alice)
		aq2 = qubit(Alice)
		nondestructiveBellStateDiscrimination( regA[i], regAB[i], aq1, aq2 )
		b1 = aq1.measure()
		b2 = aq2.measure()
		to_print = "App {}: nbsd i, b1, b2: {}, {}, {}".format(Alice.name,i,b1,b2)
		print(to_print)
		i = i+1	

	# compute the new v(t) [supposing there are other Bobs, we randomly generate v(t)]
	i = 0
	flag = 0
	while i < d:
		r = random()
		if r < q:
			if regVGlobal[i] == 1:
				regVGlobal[i] = 0
			elif regVGlobal[i] == 0:
				regVGlobal[i] = 1
			flag = 1
		i = i+1
	print(regVGlobal)
		
	sleep(3)		
		
	# notify Bob about updated shared Bell pairs
	Alice.sendClassical("Bob", "1")
	
	# update the shared Bell pairs (only those that must change) and send them to Bob
	sleep(0.5)
	i = 0
	while  i < d/2:
		# case of Bell pair that is local to Alice, thus != Beta00
		if (i in indexes):
			to_print = "App {}: i in indexes: {}".format(Alice.name,i)
			print(to_print)
			# replace Bell pair with new one in Beta00 state
			try:
				regA[i].measure() # cleaning
				regAB[i].measure() # cleaning
			except QubitNotActiveError:
				pass	
			regA[i] = Alice.createEPR("Bob")
			sleep(2)
		# apply gates to regA[i] depending on wanted new state
		if ((regVGlobal[i*2] == 0) and (regVGlobal[i*2+1] == 1)):
			# turn Beta00 to Beta01
			regA[i].X()
		elif ((regVGlobal[i*2] == 1) and (regVGlobal[i*2+1] == 0)):
			# turn Beta00 to Beta10
			regA[i].Z()
		elif ((regVGlobal[i*2] == 1) and (regVGlobal[i*2+1] == 1)):
			# turn Beta00 to Beta11
			regA[i].X()
			regA[i].Z()	
		# send Alice's qubit to Bob
		Alice.sendQubit(regA[i],"Bob")
		i = i+1	
		sleep(2)
	
	
	### QGM STEP 4
	
	to_print = "##### App {} - QGM STEP 4 #####".format(Alice.name)
	print(to_print)
	
	# get reinitialized qubits from Bob
	i = 0
	while i < d/2:
		try:
			regA[i] = Alice.recvEPR()
			to_print = "App {} received his half of the {}-th Bell pair".format(Alice.name,i)
			print(to_print)
		except CQCTimeoutError:
			to_print = "App {} did not receive his half of the {}-th Bell pair".format(Alice.name,i)
			print(to_print)		
		sleep(2)		
		i = i+1

	sleep(3)


	# perform some cleaning
	to_print = "##### App {} final cleaning #####".format(Alice.name)
	print(to_print)
	i = 0
	while i < d/2:
		try:
			regA[i].measure()
			regAB[i].measure()
		except QubitNotActiveError:
			pass	
		i = i+1
		
	# Stop the connections
	Alice.close()

##############################
main()

