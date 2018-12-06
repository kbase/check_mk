Local checks based on the check_mk docs: https://mathias-kettner.com/checkmk_localchecks.html

* check_xfs: check status of XFS filesystems.  Requires you to touch testfs file at the root of every mounted XFS filesystem.
* check_mongo: check status of mongod, including replication.  Requires separate check_mongodb.py plugin (on github, will find later)  Most of these could be put in mrpe checks, but some of the replication checks use extra output not in the plugin itself.
* check_galera: check status of a Galera cluster (probably came from a github repo somewhere originally but there are local edits)
