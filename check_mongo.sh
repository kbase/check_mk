#!/bin/bash

# for creds
MONGO_AUTH_FILE=/root/.mongorc.js
NAGIOS_PLUGIN_SCRIPT=/root/nagios-plugin-mongodb/check_mongodb.py
#NAGIOS_PLUGIN_SCRIPT=/usr/local/lib64/nagios/plugins/check_mongodb.py
# need the hostname/address that appears in rs.status()
MONGO_ADDRESS=your.host.here

mongouser=$(grep db.auth $MONGO_AUTH_FILE |cut -f2 -d "'")
mongopass=$(grep db.auth $MONGO_AUTH_FILE |cut -f4 -d "'")

NAGIOS_OPTIONS="-u $mongouser -p $mongopass -H $MONGO_ADDRESS -D"

# might be better to have a python script for this?
# or move to mrpe?
# memory_mapped needs to be able to specify params
# bash4 dictionary (aka associative array) not the most portable!
declare -A nagios_args=( ["memory_mapped"]="-W 1600 -C 2400" ["memory"]="-W 1500 -C 2000" ["page_faults"]="-W 200 -C 2000" ["replica_primary"]="-r kbrs0")

# replication_lag_percent is slow, let's leave it out
#for check in connect connections memory memory_mapped flushing last_flush_time replset_state connect_primary page_faults
for check in connect connections memory memory_mapped flushing last_flush_time replset_state replica_primary connect_primary page_faults
do
    command="$NAGIOS_PLUGIN_SCRIPT $NAGIOS_OPTIONS -A $check ${nagios_args["$check"]}"
    # only for debugging: maybe print to stderr? not useful at the moment
#    echo $command
    # execute command and get status
    out=$($command)
    status=$?
    echo "$status mongo_$check - $out"
done

# check replication_lag separately so we can put in metrics
replication_lag_out=$($NAGIOS_PLUGIN_SCRIPT $NAGIOS_OPTIONS -A replication_lag ${nagios_args["replication_lag"]})
replication_status=$?
lag=$(echo $replication_lag_out | perl -n -e '($lag)=/Lag is (\d+)/;print $lag;')
echo "$replication_status mongo_replication_lag lag=$lag $replication_lag_out"

# ideally would have python for this, or add to check_mongodb.py
timeDiffHours=$(mongo /root/getReplInfo.js |grep timeDiffHours|cut -f3 -d ' '|cut -f1 -d '.' | cut -f1 -d ',')
timeDiffHoursOut=$(mongo /root/getReplInfo.js |grep timeDiffHours|cut -f3 -d ' '|cut -f1 -d ',')
cmdStatus=$?

timeDiffHoursState=3
timeDiffHoursTxt='UNKNOWN'

timeDiffWarn=192
timeDiffCrit=24

if (( $timeDiffHours < $timeDiffWarn ))
then
    timeDiffHoursState=1
    timeDiffHoursTxt='WARNING'
fi
if (( $timeDiffHours < $timeDiffCrit ))
then
    timeDiffHoursState=2
    timeDiffHoursTxt='CRITICAL'
fi
if (( $timeDiffHours > $timeDiffWarn - 1))
then
    timeDiffHoursState=0
    timeDiffHoursTxt='OK'
fi

echo "$timeDiffHoursState mongo_replication_time_diff timeDiffHours=$timeDiffHoursOut;$timeDiffWarn;$timeDiffCrit $timeDiffHoursTxt replication time difference is $timeDiffHours hours text $timeDiffHoursOut"
