#################################################################################
## Script which count the total of the qubits exchanged during the execution   ##
## of the protocol, between each exceeding of the threshold by the root node.  ##
##																			   ##
## It is executed on the log file of each node, contained in the 'log' folder. ##
#################################################################################

import os, datetime

dir = "log"

def main():
	# Get the number of files in the directory
	numFiles = len(next(os.walk(dir))[2])
	
	precRowDateTime = datetime.datetime.now()
	
	with open(os.path.join("", "results.txt"), "w") as f_out:
		with open(os.path.join(dir, "node0.txt"), "r") as node0:
			i = 0
			for row in node0:
				sentQubits = 0
				receivedQubits = 0
				rowSplitted = row.split("_")
				rowDateTime = datetime.datetime.strptime(rowSplitted[0], "%Y-%m-%d %H:%M:%S.%f")
				if (i == 0):
					precRowDateTime = rowDateTime - datetime.timedelta(hours=1)
				print("preThresholdViolation: "+str(precRowDateTime))
				print("newThresholdViolation: "+str(rowDateTime))
				f_out.write("preThresholdViolation: {}\n".format(str(precRowDateTime)))
				f_out.write("newThresholdViolation: {}\n".format(str(rowDateTime)))
				sentQubits += getQubitNumber(rowSplitted[3])
				receivedQubits += getQubitNumber(rowSplitted[4])
				for i in range(1, numFiles):
					nodeFile = "node"+str(i)+".txt"
					with open(os.path.join(dir, nodeFile), "r") as nodex:
						for row2 in nodex:
							row2Splitted = row2.split("_")
							row2DateTime = datetime.datetime.strptime(row2Splitted[0], "%Y-%m-%d %H:%M:%S.%f")
							# precRowDateTime < row2DateTime <= rowDateTime
							if (precRowDateTime < row2DateTime and row2DateTime <= rowDateTime):
								sentQubits += getQubitNumber(row2Splitted[3])
								receivedQubits += getQubitNumber(row2Splitted[4])
								#print(row2)
				print("Qubit Sent = {}".format(sentQubits))
				print("Qubit Received = {}\n".format(receivedQubits))
				f_out.write("Qubit Sent = {}\n".format(sentQubits))
				f_out.write("Qubit Received = {}\n\n".format(receivedQubits))
				precRowDateTime = rowDateTime
				i += 1
			
def getQubitNumber(n):
	result = n.split(":")
	return int(result[1])
	
main()