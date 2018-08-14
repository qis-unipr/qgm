Quantum Geometric Monitoring (QGM) - 2 - test QGM-Tree with SimulaQron
===============================================

In this example we have N nodes forming a binary tree.
Every node is able to play the coordinator and the producer.

Current version has N=3 nodes: node0 is the root of the tree 
and plays the coordinator for its children node1 and node2.

With the exception of node0, every other node plays the producer with respect to its parent.

First, you need to install SimulaQron - the version under development, which has qubit transmission timouts. 
https://stephaniewehner.github.io/SimulaQron/PreBetaDocs/GettingStarted.html#installation

You may need to install Cython as well: pip install Cython

Then, put the testQGMTree folder in SimulaQron's one:
SimulaQron/examples/cdc/pythonLib/testQGMTree/

Then, enter SimulaQron's folder and edit 
- config/appNodes.cfg
- config/cqcNodes.cfg
- config/virtualNodes.cfg
in order to limit the number of virtual nodes and CQC servers (node0, node1, node2).

Edit cqc/backend/cqcConfig.py in order to set:
CQC_CONF_RECV_TIMEOUT=20 # (x 100ms)
CQC_CONF_RECV_EPR_TIMEOUT=20 # (x 100ms)

Finally, put myStarter.sh into the SimulaQron/run/ folder,
enter that folder and do the following:
source myStarter.sh

Open another shell and do the following:
cd examples/cqc/pythonLib/testQGMTree
source run.sh

Tested with Python 3.6 and 3.7.
