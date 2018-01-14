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
	reg = []

	# QGM STEP 1

	# Receive qubits
	i = 0
	while i < d/2:
		reg.append(Bob.recvEPR())
		i = i+1

	# QGM STEP 2
	
	# randomly change some bits in the local state register
	to_print = "App {}: QGM STEP 2".format(Bob.name)
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
		# notify Alice about local violation (sendClassical)
		Bob.sendClassical("Alice", "1")
		# change the corresponding Bell pairs and send changed qubits to Alice
		sleep(0.5)
		i = 0
		while  i < d/2:
			# from Alice recv classical i (trick to simulate slotted communication)
			#data=Bob.recvClassical() # TO DO: get sender name			#message=list(data)			#b=message[0]
			#print(b)
			if ((regVLocal[i*2] != 0) or (regVLocal[i*2+1] != 0)):
				# TODO apply X, Z or XZ to reg[i]
				Bob.sendQubit(reg[i],"Alice")
			else:	
				print("send nothing")
			i = i+1	
			sleep(2)
	else:
		Bob.sendClassical("Alice", "0") # this is a trick to unblock Alice
	
	sleep(3)
	
	# QGM STEP 3
	
	# wait for notification about updated qubits ready for being transmitted by Alice
	
	# QGM STEP 4
	
	# receive all the updated Bell pairs from Alice
	# reinitialize Bell pairs to the 00 state
	# send reinitialized qubits to Alice
	# repeat from STEP 2	
	
	# perform some cleaning
	i = 0
	while i < d/2:
		try:
			reg[i].measure()
		except QubitNotActiveError:
			pass	
		i = i+1	
	
	# Stop the connection
	Bob.close()

##############################
main()

