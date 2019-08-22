#!/bin/bash

mysqlhost='localhost'
mysqluser=$(grep user /root/.my.cnf|cut -f2 -d '=')		
password=$(grep password /root/.my.cnf|cut -f2 -d '=')

r1=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'Threads_connected'"|cut -f 2)

echo $r1
