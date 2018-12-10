# Geometric Monitoring (GM)

Implementation and testing of the GM-Tree protocol with [SimulaQron](http://www.simulaqron.org/).

## Getting Started

In this example we have N nodes forming a binary tree.
The root of the tree is named 'node0', which can only play the role of the coordinator.
Every other node can play both the role of coordinator and producer.

Only leaf nodes (i.e. nodes without child nodes) can suffer a local violation.
Each sub-tree maintains its own global sub-status that communicates to the upper parent node only if it exceeds a pre-set threshold.

When a leaf node suffers a local violation, it communicates it to the parent node, which acquires the status of the other brother node.
Subsequently, it averages the two states and checks whether the threshold has been exceeded.
If the threshold has been exceeded, this procedure is repeated in the upper level sub-tree.

*Note: the current version has been tested with a maximum of 7 nodes.*

### Prerequisites

* [SimulaQron](http://www.simulaqron.org/)

  Please refer to the [Getting started](https://softwarequtech.github.io/SimulaQron/html/GettingStarted.html) page of the SimulaQron guide for installation instructions.

* Python module [bitarray](https://pypi.org/project/bitarray/)
  ```
  pip install bitarray
  ```

### Installing

1. Clone the testGMTree folder in: *SimulaQron/examples/cdc/pythonLib*.

2. Move the *myStarter.sh* file to *SimulaQron/run*.

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
* In the *qgmnode.py* file you can change the value of the variable 'd' where d is the number of bits used to represent the state of each node.
* In the *qgmnode.py* file you can change the value of the variable 't' if you want to change the threshold value.

### Logging

For each node a log file is created in the *log* folder.
For the normal nodes a row is written to the log file each time the node exceeds the threshold.
Every row shows a timestamp followed by how many bits the node has sent/received from the previous exceeding of the threshold.
For leaf nodes instead, a row is written to the log file each time the node suffered a local violation.
Each row reports a timestamp followed by the number of bits sent/received from the last local violation that the node suffered.

In the main folder there is a script called *qubitCounter.py* which uses the log files to calculate the total qubits exchanged between each threshold overrun by the root node.

You can run this script by simply typing:
```
python bitCounter.py
```

## License

Please refer to the [LICENSE](https://github.com/qis-unipr/QuantumNetworking/blob/master/LICENSE) file for details.