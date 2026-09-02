#!/usr/bin/env python3

"""
For every CronJob in the cluster, find its child Jobs
(via ownerReferences) and report any which failed.
Will automatically pick up new CronJob objects.

Ensure that `ttlSecondsAfterFinished` is set to a high enough value
(e.g., 172800 for two days) in the CronJob.
Otherwise, Job objects will be purged too early, and the script
could report an inaccurate status.

Nagios exit statuses (for use with mrpe):
Exits 2 if most recent Job in any CronJob failed
Exits 1 if any Job failed but a more recent Job of that CronJob succeeded
Exits 0 if all Jobs succeeded

Requires: pip install kubernetes, credentials saved in default location
"""

import kubernetes
import sys

def load_kube_config():
    # Tries in-cluster config first (e.g. running as a Pod), falls back
    # to your local kubeconfig (~/.kube/config or $KUBECONFIG).
    # (for use in check_mk, will likely prefer $HOME/.kube/config
    try:
        kubernetes.config.load_incluster_config()
    except kubernetes.config.ConfigException:
        kubernetes.config.load_kube_config()


def main():
    load_kube_config()
    try:
        batch = kubernetes.client.BatchV1Api()
    except:
        print("can't connect to k8s")
    
    try:
        cronjobs = batch.list_cron_job_for_all_namespaces().items
        jobs = batch.list_job_for_all_namespaces().items
    except:
        print("can't get CronJobs from k8s")
    
    # Index jobs by their owning CronJob's uid
    jobs_by_cronjob_uid = {}
    for job in jobs:
        for ref in job.metadata.owner_references or []:
            if ref.kind == "CronJob":
                try:
                    jobs_by_cronjob_uid.setdefault(ref.uid, []).append(job)
                except:
                    print("can't get Jobs from k8s")

    cronjob_names = []
    failed_children = []
    status=3

    for cj in cronjobs:
        ns = cj.metadata.namespace
        name = cj.metadata.name
        uid = cj.metadata.uid

        cronjob_names.append(cj.metadata.namespace+'/'+cj.metadata.name)
        children = sorted(
            jobs_by_cronjob_uid.get(uid, []),
            key=lambda j: (
                (j.status.start_time or j.metadata.creation_timestamp).timestamp()
                if (j.status.start_time or j.metadata.creation_timestamp)
                else 0.0
            ),
        )

        cronjobstatus=3
        # setting the status like this depends on jobs being sorted by date
        # which the script doesn't currently check for
        for job in children:
            #print (str(job))
            conditions = job.status.conditions or []
            if any(c.type == "Failed" and c.status == "True" for c in conditions):
                failed_children.append(f"{job.metadata.namespace}/{job.metadata.name}")
                cronjobstatus=2
            # explicitly look for success
            elif any(c.type == "Complete" and c.status == "True" for c in conditions):
                if (len(failed_children) > 0):
                    cronjobstatus=1
                else:
                    cronjobstatus=0
            # otherwise this Job object won't change cronjobstatus

        # set global status based on status of previous and current CronJob objects
        if (status == 3):
            status=cronjobstatus
        if (cronjobstatus > status and cronjobstatus != 3):
            status=cronjobstatus

    if failed_children:
        print(f"failed CronJobs:  {', '.join(failed_children)} ; CronJobs checked: {', '.join(cronjob_names)}")
    elif status == 0:
#        print(str(status) + f" ok      {ns}/{name}  ({len(children)} job(s))")
        print(f"all CronJobs OK, CronJobs checked: {', '.join(cronjob_names)}")
    else:
        print(f"status of CronJobs unknown, CronJobs checked: {', '.join(cronjob_names)}")

    # required in order to exit script with correct exit value
    return status

if __name__ == "__main__":
    sys.exit(main())    
