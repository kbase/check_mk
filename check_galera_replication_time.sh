#!/bin/bash
PROGNAME=`basename $0`
VERSION="Version 1.0,"
AUTHOR="Guillaume Coré <g@fridim.org>, Keith Keller <kkeller@lbl.gov>"

### THIS SCRIPT RUNS FOR AT LEAST ONE MINUTE!
### If using with check_mk be sure to have it cache results for at least five minutes.

ST_OK=0
ST_WR=1
ST_CR=2
ST_UK=3

print_version() {
  echo "$VERSION $AUTHOR"
}

print_help() {
  print_version $PROGNAME $VERSION
  echo ""
  echo "$PROGNAME is a Nagios plugin to monitor Galera cluster status."
  echo ""
  echo "### $PROGNAME runs for at least one minute! ###"
  echo "### Be sure to set timeouts appropriately. ###"
  echo ""
  echo "$PROGNAME -u USER -p PASSWORD [-H HOST] [-P PORT] [-w FLOAT] [-c FLOAT]"
  echo ""
  echo "Options:"
  echo "  u)"
  echo "    MySQL user."
  echo "  p)"
  echo "    MySQL password."
  echo "  H)"
  echo "    MySQL host. Default is $mysqlhost."
  echo "  P)"
  echo "    MySQL port. Default is $port."
  echo "  w)"
  echo "    Sets minimum minutes (as a float) of replication time when WARNING is raised. (default is $warn)."
  echo "  c)"
  echo "    Sets minimum minutes (as a float) of replication time when CRITICAL is raised. (default is $crit)."
  exit $ST_UK
}

# default values
crit=1440.0
warn=2880.0
port='3306'
mysqlhost='localhost'

while getopts “hvu:p:H:P:w:c:” OPTION; do
  case $OPTION in
    h)
      print_help
      exit $ST_UK
      ;;
    v)
      print_version $PROGNAME $VERSION
      exit $ST_UK
      ;;
    u)
      mysqluser=$OPTARG
      ;;
    p)
      password=$OPTARG
      ;;
    H)
      mysqlhost=$OPTARG
      ;;
    P)
      port=$OPTARG
      ;;
    w)
      warn=$OPTARG
      ;;
    c)
      crit=$OPTARG
      ;;
    ?)
      echo "Unknown argument: $1"
      print_help
      exit $ST_UK
      ;;
  esac
done

mysqluser=$(grep user /root/.my.cnf|cut -f2 -d '=')		
password=$(grep password /root/.my.cnf|cut -f2 -d '=')

if [ -z "$warn" ]; then
  warn=$crit
fi

# MANDATORY args
if [ -z "$mysqluser" ]; then
  echo "argument -u missing"
  print_help
  exit $ST_UK
fi

if [ -z "$password" ]; then
  echo "argument -p missing"
  print_help
  exit $ST_UK
fi

r1=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "SET @start := (SELECT SUM(VARIABLE_VALUE/1024/1024) FROM information_schema.global_status WHERE VARIABLE_NAME LIKE 'WSREP%bytes'); do sleep(60); SET @end := (SELECT SUM(VARIABLE_VALUE/1024/1024) FROM information_schema.global_status WHERE VARIABLE_NAME LIKE 'WSREP%bytes'); SET @gcache := (SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(@@GLOBAL.wsrep_provider_options,'gcache.size = ',-1), 'M', 1)); COALESCE(SELECT ROUND(@gcache/round((@end - @start),2),2),0)") # time to full

state_text="UNKNOWN"

if [ $(echo "$r1 > $warn"|bc ) = 1 ]; then
  ST_FINAL=${ST_FINAL-$ST_OK}
  state_text="$ST_FINAL mysql_galera_replication_time - OK - replication time = $r1"
elif [ $(echo "$r1 < $crit"|bc ) = 1 ]; then
  ST_FINAL=$ST_CR
  state_text="$ST_FINAL mysql_galera_replication_time - CRITICAL - replication time = $r1"
elif [ $(echo "$r1 < $warn"|bc ) = 1 ]; then
  ST_FINAL=${ST_FINAL-$ST_WR}
  state_text="$ST_FINAL mysql_galera_replication_time - WARNING - replication time = $r1"
else
  ST_FINAL=${ST_FINAL-$ST_UK}
  state_text="$ST_FINAL mysql_galera_replication_time - UNKNOWN - $ST_UK"
fi

echo "$state_text |repltime=$r1;$warn;$crit"

exit $ST_FINAL
