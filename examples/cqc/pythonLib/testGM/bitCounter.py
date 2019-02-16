##################################################################################
## Script which count the total of the bits exchanged during the execution      ##
## of the protocol, between each exceeding of the threshold by the root node.   ##
##																			    ##
## It is executed on the log file of each node, contained in the 'log2' folder. ##
##################################################################################

import os, datetime, math

dir = "log2"

def main():
	# Get the number of files in the directory
	numFiles = len(next(os.walk(dir))[2])
	tot_exch_bit = 0
	tot_step234 = 0
	numChildNodes = numFiles - 1
	
	precRowDateTime = datetime.datetime.now()
	
	with open(os.path.join("", "results2.txt"), "w") as f_out:
		with open(os.path.join(dir, "node0.txt"), "r") as node0:
			i = 0
			for row in node0:
				sentBits = 0
				receivedBits = 0
				rowSplitted = row.split("_")
				rowDateTime = datetime.datetime.strptime(rowSplitted[0], "%Y-%m-%d %H:%M:%S.%f")
				if (i == 0):
					precRowDateTime = rowDateTime - datetime.timedelta(hours=1)
				f_out.write("{}.newThresholdViolation: {}\n".format(i, str(rowDateTime)))
				f_out.write(row)
				sentBits += getBitNumber(rowSplitted[3])
				receivedBits += getBitNumber(rowSplitted[4])
				for j in range(1, numFiles):
					nodeFile = "node"+str(j)+".txt"
					with open(os.path.join(dir, nodeFile), "r") as nodex:
						for row2 in nodex:
							row2Splitted = row2.split("_")
							row2DateTime = datetime.datetime.strptime(row2Splitted[0], "%Y-%m-%d %H:%M:%S.%f")
							if (precRowDateTime < row2DateTime and row2DateTime <= rowDateTime):
								sentBits += getBitNumber(row2Splitted[3])
								receivedBits += getBitNumber(row2Splitted[4])
								tot_step234 += 1
								f_out.write(row2)
				tot_exch_bit += sentBits
				f_out.write("-->Sent={}\n".format(sentBits))
				f_out.write("-->Received={}\n\n".format(receivedBits))
				precRowDateTime = rowDateTime
				i += 1
		f_out.write("\nTotal Bits Exchanged = {}".format(tot_exch_bit))
		tot_step234 /= numChildNodes
		f_out.write("\nTotal Step234 = {}".format(tot_step234))
		f_out.write("\nAvg Bits Exchanged for each round = {}".format(round(tot_exch_bit/tot_step234, 2)))
			
def getBitNumber(n):
	result = n.split(":")
	return int(result[1])
	
main()