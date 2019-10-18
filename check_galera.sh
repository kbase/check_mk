#!/bin/bash
PROGNAME=`basename $0`
VERSION="Version 1.0,"
AUTHOR="Guillaume Coré <g@fridim.org>"

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
  echo "$PROGNAME -u USER -p PASSWORD [-H HOST] [-P PORT] [-w SIZE] [-c SIZE] [-f FLOAT] [-0]"
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
  echo "    Sets minimum number of nodes in the cluster when WARNING is raised. (default is $warn)."
  echo "  c)"
  echo "    Sets minimum number of nodes in the cluster when CRITICAL is raised. (default is $crit)."
  echo "  f)"
  echo "    Sets critical value of wsrep_flow_control_paused (default is $fcpcrit ; warning is $fcpwarn and not currently configurable)."
  echo "  0)"
  echo "    Rise CRITICAL if the node is not primary"
  exit $ST_UK
}

# default values
crit=1
warn=2
port='3306'
mysqlhost='localhost'
fcpwarn=0.1
fcpcrit=0.15

while getopts “hvu:p:H:P:w:c:f:0” OPTION; do
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
    f)
      fcpcrit=$OPTARG
      ;;
    0)
      primary='TRUE'
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

r1=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'wsrep_cluster_size'"|cut -f 2) # 3  (GALERA_CLUSTER_SIZE)
r2=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'wsrep_cluster_status'"|cut -f 2) # Primary
r3=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'wsrep_flow_control_paused'"|cut -f 2) # < 0.1
r4=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'wsrep_ready'"|cut -f 2)  # ON
r5=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'wsrep_connected'"|cut -f 2)  # ON
r6=$(mysql -h$mysqlhost -P$port -u$mysqluser -p$password -B -N -e "show status like 'wsrep_local_state_comment'"|cut -f 2)  # Synced

extra_text="no extra notes"

if [ -z "$r3" ]; then
  extra_text="wsrep_flow_control_paused is empty"
  ST_FINAL=$ST_UK
fi

# this gets confused if mysql returns a value in scientific notation
# (e.g., 6.36039e-05)
fcpvalue=$(printf "%.12f" $r3)
if [ $(echo "$fcpvalue > $fcpwarn" | bc) = 1 ]; then
  extra_text="wsrep_flow_control_paused is $fcpvalue > $fcp"
  ST_FINAL=$ST_WR
  if [ $(echo "$fcpvalue > $fcpcrit" | bc) = 1 ]; then
    ST_FINAL=$ST_CR
  fi
fi

if [ "$r6" != 'Synced' ]; then
  extra_text="node is not synced"
  ST_FINAL=$ST_WR
fi

if [ "$primary" = 'TRUE' ]; then
  if [ "$r2" != 'Primary' ]; then
    extra_text="node is not primary"
    ST_FINAL=$ST_CR
  fi
fi

if [ "$r4" != 'ON' ]; then
  extra_text="node is not ready"
  ST_FINAL=$ST_CR
fi

if [ "$r5" != 'ON' ]; then
  extra_text="node is not connected"
  ST_FINAL=$ST_CR
fi

state_text="UNKNOWN"

if [ $r1 -gt $warn ]; then
  ST_FINAL=${ST_FINAL-$ST_OK}
  state_text="$ST_FINAL mysql_galera - OK - number of NODES = $r1"
elif [ $r1 -le $crit ]; then
  ST_FINAL=$ST_CR
  state_text="$ST_FINAL mysql_galera - CRITICAL - number of NODES = $r1"
elif [ $r1 -le $warn ]; then
  ST_FINAL=${ST_FINAL-$ST_WR}
  state_text="$ST_FINAL mysql_galera - WARNING - number of NODES = $r1"
else
  ST_FINAL=${ST_FINAL-$ST_UK}
  state_text="$ST_FINAL mysql_galera - UNKNOWN - $ST_UK"
fi

echo "$state_text ( $extra_text ) |fcpaused=$fcpvalue;$fcpwarn;$fcpcrit"

exit $ST_FINAL
