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

from time import sleep

##############################
#
# main
#
def main():

	# Initialize the connection
	Alice=CQCConnection("Alice")
	
	# Size of monitored data
	d = 4

	# QGM STEP 1
	
	# Create qubit register for EPR pairs
	reg = []
	i = 0
	while i < d/2:
		reg.append(Alice.createEPR("Bob"))
		i = i+1
		
	# QGM STEP 2
	
	# wait for notification from Bob about local violation 
	to_print = "App {}: QGM STEP 2".format(Alice.name)
	print(to_print)
		
	data=Alice.recvClassical() # TODO: get sender name	message=list(data)	b=message[0]
	to_print="App {}: received notification from Bob: {}".format(Alice.name,b)
	print(to_print)
	if b == 1:
		# get changed qubits from Bob 
		i = 0
		while  i < d/2:
			try:
				q=Alice.recvQubit()
				print("Alice received a qubit")
			except CQCTimeoutError:
				print("Alice did not receive a qubit")
			i = i+1
	
	# QGM STEP 3
	
	# perform Bell state discrimination by nondestructive measurement on the local Bell pairs
	# compute the new v(t) 
	# update the shared Bell pairs (only those that must change)
	# notify Bob for updated qubits ready for being transmitted
	
	# QGM STEP 4
	
	# send all the updated Bell pairs to Bob
	# get reinitialized qubits from Bob
	# repeat from STEP 2

	sleep(3)

	# perform some cleaning
	i = 0
	while i < d/2:
		try:
			reg[i].measure()
		except QubitNotActiveError:
			pass	
		i = i+1
		
	# Stop the connections
	Alice.close()

##############################
main()

