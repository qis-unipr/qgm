###################################################################################
## Script that prints the local state value of each node whenever the root node  ##
## exceeds the preset threshold. It also calculates the percentage error between ##
## the root node state and the local state average of all other nodes of the     ##
## binary tree.                                                                  ##
##																			     ##
## It is executed on the log file of each node, contained in the 'log' folder.   ##
###################################################################################

import os, datetime, math

dir = "log"

# Bit number
d = 4

def main():
	# Get the number of files in the directory
	numFiles = len(next(os.walk(dir))[2])
	diff_list = []
	localStates = [0] * (numFiles - 1)
	
	statesNumber = 2**d
	
	with open(os.path.join("", "results.txt"), "w") as f_out:
		with open(os.path.join(dir, "node0.txt"), "r") as node0:
			i = 0
			for row in node0:
				rowSplitted = row.split("_")
				rowDateTime = datetime.datetime.strptime(rowSplitted[0], "%Y-%m-%d %H:%M:%S.%f")
				rootLocalState = int(rowSplitted[1], 2)
				for j in range(1, numFiles):
					nodeFile = "node"+str(j)+".txt"
					with open(os.path.join(dir, nodeFile), "r") as nodex:
						for row2 in nodex:
							row2Splitted = row2.split("_")
							row2DateTime = datetime.datetime.strptime(row2Splitted[0], "%Y-%m-%d %H:%M:%S.%f")
							if (rowDateTime > row2DateTime):
								localStates[j-1] = int(row2Splitted[1], 2)
							else:
								continue
				totLocalStates = 0
				for z in range(0, numFiles-1):
					totLocalStates += localStates[z]
				avgLocalStates = round(totLocalStates/(numFiles-1), 2)
				diff = round(abs(rootLocalState - avgLocalStates), 2)
				diff_list.append(diff)
				f_out.write("{}.G12={}__avgLocalStates={}__Difference={}\n".format(i, rootLocalState, avgLocalStates, diff))
				i += 1
				
		tot_diff = 0
		i = 0
		while i < len(diff_list):
			tot_diff += diff_list[i]
			i += 1
		avg_diff = tot_diff / i
		perc_err = (avg_diff / statesNumber) * 100
		
		j = 0
		square_sum = 0
		while j < len(diff_list):
			diff_list[j] -= avg_diff
			diff_list[j] = diff_list[j] * diff_list[j]
			square_sum += diff_list[j]
			j += 1
		
		variance = square_sum / (j - 1)
		std_dev = math.sqrt(variance)
		marg_err = 1.96 * (std_dev / math.sqrt(j))
		perc_marg_err = (marg_err / 16) * 100
		
		f_out.write("\nAverage of all differences = {}".format(round(avg_diff, 2)))
		f_out.write("\nStandard Deviation = {}".format(round(std_dev, 2)))
		f_out.write("\nMargin Error = {}".format(round(marg_err, 2)))
		f_out.write("\nAvg Diff Percentage Error = {}%".format(round(perc_err, 2)))
		f_out.write("\nMargin Percentage Error = {}%".format(round(perc_marg_err, 2)))
	
main()