#!/bin/bash

mysqlhost='localhost'
port=3306
mysqluser=$(grep user /root/.my.cnf|cut -f2 -d '=')		
password=$(grep password /root/.my.cnf|cut -f2 -d '=')

ST_OK=0
ST_WR=1
ST_CR=2
ST_UK=3

while getopts “hvu:p:H:P:w:c:f:0” OPTION; do
  case $OPTION in
    w)
      warn=$OPTARG
      ;;
    c)
      crit=$OPTARG
      ;;
    ?)
      echo "Unknown argument: $1"
      exit $ST_UK
      ;;
  esac
done

r1=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'Threads_connected'"|cut -f 2)
r2=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'Max_used_connections'"|cut -f 2)

if [ $r1 -le $warn ]; then
  ST_FINAL=${ST_FINAL-$ST_OK}
  ST_TEXT='OK'
#  echo "$ST_FINAL mysql_galera_threads - OK - number of threads = $r1"
elif [ $r1 -gt $crit ]; then
  ST_FINAL=$ST_CR
  ST_TEXT='CRITICAL'
#  echo "$ST_FINAL mysql_galera_threads - CRITICAL - number of threads = $r1"
elif [ $r1 -gt $warn ]; then
  ST_FINAL=${ST_FINAL-$ST_WR}
  ST_TEXT='WARNING'
#  echo "$ST_FINAL mysql_galera_threads - WARNING - number of threads = $r1"
else
  ST_FINAL=${ST_FINAL-$ST_UK}
  ST_TEXT='UNKNOWN'
#  echo "$ST_FINAL mysql_galera_threads - UNKNOWN - $ST_UK"
fi

if [ $r2 -le $warn ]; then
  ST2_FINAL=${ST2_FINAL-$ST_OK}
  ST2_TEXT='OK'
#  echo "$ST_FINAL mysql_galera_threads - OK - number of threads = $r1"
elif [ $r2 -gt $crit ]; then
  ST2_FINAL=$ST_CR
  ST2_TEXT='CRITICAL'
#  echo "$ST_FINAL mysql_galera_threads - CRITICAL - number of threads = $r1"
elif [ $r2 -gt $warn ]; then
  ST2_FINAL=${ST2_FINAL-$ST_WR}
  ST2_TEXT='WARNING'
#  echo "$ST_FINAL mysql_galera_threads - WARNING - number of threads = $r1"
else
  ST2_FINAL=${ST2_FINAL-$ST_UK}
  ST2_TEXT='UNKNOWN'
#  echo "$ST_FINAL mysql_galera_threads - UNKNOWN - $ST_UK"
fi

echo "$ST_FINAL mysql_threads - $ST_TEXT number of threads = $r1 |threads=$r1;$warn;$crit"
# not really ready yet
#echo "$ST2_FINAL mysql_max_threads - $ST2_TEXT max number of threads = $r2 |threads=$r2;$warn;$crit"

exit $ST_FINAL
