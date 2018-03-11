Quantum Geometric Monitoring (QGM) - 1 - test QGM with SimulaQron
===============================================

In this example Alice is the Coordinator and Bob is a remote site. They run the QGM protocol.

First, you need to install SimulaQron - the version under development, which has qubit transmission timouts. 
https://stephaniewehner.github.io/SimulaQron/PreBetaDocs/GettingStarted.html#installation

Then, put the testQGM folder in SimulaQron's one:
SimulaQron/examples/cdc/pythonLib/testQGM/

Then, enter SimulaQron's folder and edit 
- config/virtualNodes.cfg
- config/cqcNodes.cfg
- config/classicalNet.cfg
- startVNodes.sh 
- startCQCNodes.sh
in order to limit the number of virtual nodes and CQC servers (Alice and Bob are enough for this example).

Edit cqc/backend/cqcConfig.py in order to set:
CQC_CONF_RECV_TIMEOUT=20 # (x 100ms)
CQC_CONF_RECV_EPR_TIMEOUT=20 # (x 100ms)

Finally, enter SimulaQron's folder and do the following:
./run/startAll.sh    

Open another shell and do the following:
cd examples/cqc/pythonLib/testQGM
./doNew.sh (starts the processes)
