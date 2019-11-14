
ps aux | grep python3 | grep Test | awk {'print $2'} | xargs kill -9
sh run.sh
