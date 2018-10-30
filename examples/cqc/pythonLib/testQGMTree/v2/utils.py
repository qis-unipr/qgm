
from SimulaQron.general.hostConfig import *
from SimulaQron.cqc.backend.cqcHeader import *
from SimulaQron.cqc.pythonLib.cqc import *

##############################
#
# Performs nondestructive discrimination of Bell state of qubits (qA,qB).
# By measuring the ancilla qubits (aq1,aq2) in the computational basis,
# we obtain: 
# (0,0) for |phi+>
# (1,0) for |phi->
# (0,1) for |psi+>
# (1,1) for |psi->
#
def nondestructiveBellStateDiscrimination( qA, qB, aq1, aq2 ):
	aq1.H()
	aq1.cnot(qA)
	aq1.cnot(qB)
	aq1.H()
	qA.cnot(aq2)
	qB.cnot(aq2)
	return
##############################

