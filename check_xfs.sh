#!/bin/bash

if type waitmax >/dev/null
then
    STAT_VERSION=$(stat --version | head -1 | cut -d" " -f4)
    STAT_BROKE="5.3.0"

    sed -n '/ xfs\? /s/[^ ]* \([^ ]*\) .*/\1/p' < /proc/mounts | grep -v var/lib/kubelet/pods |
#    sed -n '/ xfs\? /s/[^ ]* \([^ ]*\) .*/\1/p' < /root/dummyMounts |
        while read MP
        do
         if [ $STAT_VERSION != $STAT_BROKE ]; then
            waitmax -s 9 2 stat -f -c "0 xfs_mountpoint_$MP - OK %b %f %a %s" "$MP/testfs" || \
                echo "2 xfs_mountpoint_$MP - CRITICAL hanging 0 0 0 0"
         else
            waitmax -s 9 2 stat -f -c "0 xfs_mountpoint_$MP - OK %b %f %a %s" "$MP/testfs" && \
            printf '\n'|| echo "2 xfs_mountpoint_$MP - CRITICAL hanging 0 0 0 0"
         fi

         # adding crude write test
         touch $MP/testwritefs 2> /tmp/testwriteerr
         status=$?
         if [ $status -eq 0 ]; then
           echo "0 xfs_write_$MP - OK"
         else
           echo "2 xfs_write_$MP - CRITICAL - exit status $status - err $(cat /tmp/testwriteerr)"
         fi

        done
fi
