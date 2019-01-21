##################################################################################
## Script which count the total of the qubits exchanged during the execution    ##
## of the protocol, between each exceeding of the threshold by the root node.   ##
##																			    ##
## It is executed on the log file of each node, contained in the 'log2' folder. ##
##################################################################################

import os, datetime, math

dir = "log2"

def main():
	# Get the number of files in the directory
	numFiles = len(next(os.walk(dir))[2])
	tot_exch_qubit = 0
	tot_step234 = 0
	
	precRowDateTime = datetime.datetime.now()
	
	with open(os.path.join("", "results2.txt"), "w") as f_out:
		with open(os.path.join(dir, "node0.txt"), "r") as node0:
			i = 0
			for row in node0:
				sentQubits = 0
				receivedQubits = 0
				rowSplitted = row.split("_")
				rowDateTime = datetime.datetime.strptime(rowSplitted[0], "%Y-%m-%d %H:%M:%S.%f")
				if (i == 0):
					precRowDateTime = rowDateTime - datetime.timedelta(hours=1)
				f_out.write("{}.newThresholdViolation: {}\n".format(i, str(rowDateTime)))
				f_out.write(row)
				sentQubits += getQubitNumber(rowSplitted[3])
				receivedQubits += getQubitNumber(rowSplitted[4])
				for j in range(1, numFiles):
					nodeFile = "node"+str(j)+".txt"
					with open(os.path.join(dir, nodeFile), "r") as nodex:
						for row2 in nodex:
							row2Splitted = row2.split("_")
							row2DateTime = datetime.datetime.strptime(row2Splitted[0], "%Y-%m-%d %H:%M:%S.%f")
							if (precRowDateTime < row2DateTime and row2DateTime <= rowDateTime):
								sentQubits += getQubitNumber(row2Splitted[3])
								receivedQubits += getQubitNumber(row2Splitted[4])
								tot_step234 += 1
								f_out.write(row2)
				tot_exch_qubit += sentQubits
				f_out.write("-->Sent={}\n".format(sentQubits))
				f_out.write("-->Received={}\n\n".format(receivedQubits))
				precRowDateTime = rowDateTime
				i += 1
		f_out.write("\nTotal Qubits Exchanged = {}".format(tot_exch_qubit))
		tot_step234 /= 2
		f_out.write("\nTotal Step234 = {}".format(tot_step234))
		f_out.write("\nAvg Qubits Exchanged for each round = {}".format(round(tot_exch_qubit/tot_step234, 2)))
			
def getQubitNumber(n):
	result = n.split(":")
	return int(result[1])
	
main()