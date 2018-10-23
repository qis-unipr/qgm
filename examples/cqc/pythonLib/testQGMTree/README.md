# Quantum Geometric Monitoring (QGM)

Implementation and testing of the QGM-Tree protocol with [SimulaQron](http://www.simulaqron.org/).

## Getting Started

In this example we have N nodes forming a binary tree.
The root of the tree is node0, which can only play the role of the coordinator.
Every other node can play both the role of coordinator and producer.

*Note: the current version has been tested with a maximum of 7 nodes.*

### Prerequisites

* [SimulaQron](http://www.simulaqron.org/)

  Please refer to the [Getting started](https://softwarequtech.github.io/SimulaQron/html/GettingStarted.html) page of the SimulaQron guide for installation instructions.

* Python module [bitarray](https://pypi.org/project/bitarray/)
  ```
  pip install bitarray
  ```

### Installing

1. Clone the testQGMTree folder in: *SimulaQron/examples/cdc/pythonLib/testQGMTree*.

2. Enter in: *SimulaQron/config* and edit the following files:
   - *appNodes.cfg*
   - *cqcNodes.cfg*
   - *virtualNodes.cfg*

   in order to set the number of virtual nodes and CQC servers (node0, node1, node2, ...).
   
   In the same folder edit the *settings.ini* file in order to set:
   ```
   maxqubits_per_node = 100
   ```

3. Enter in: *SimulaQron/cqc/backend* and edit the *cqcConfig.py* file in order to set:
   ```
   CQC_CONF_RECV_TIMEOUT=25 # (x 100ms)
   CQC_CONF_RECV_EPR_TIMEOUT=25 # (x 100ms)
   ```

4. Move the *myStarter.sh* file to *SimulaQron/run*.

## Running

1. Open a first shell and execute:
   ```
   cd SimulaQron/run
   sh myStarter.sh
   ```

2. Open a second shell and execute:
   ```
   cd examples/cqc/pythonLib/testQGMTree
   sh run.sh
   ```

*Note: the current version has been tested with Python 3.6 and 3.7*

### Settings

If you want to set up a different network of nodes you can change some parameters in the following files:
* In the *run.sh* file you can change the number of nodes, and specify for each node its name and the probability that it will suffer a local violation.
  Note: if you change the number of nodes you also need to update the value of the 'n' variable in the main function of the *qgmnode.py* file.
* In the *qgmnode.py* file you can change the value of the variable 'd' where d/2 represents the number of qubits used by each node.

## License

Please refer to the [LICENSE.txt](https://github.com/qis-unipr/QuantumNetworking/blob/master/LICENSE.txt) file for details.