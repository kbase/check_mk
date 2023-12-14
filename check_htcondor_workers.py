#!/usr/bin/env python

import htcondor

def get_worker_status():
    coll = htcondor.Collector()
    ads = coll.query(htcondor.AdTypes.Startd, projection=["Name", "node_is_healthy"])

    healthy_workers = []
    unhealthy_workers = []

    for ad in ads:
        name = ad.get('Name', 'Unknown')
        is_healthy = ad.get('node_is_healthy', False)

        if is_healthy:
            healthy_workers.append(name)
        else:
            unhealthy_workers.append(name)

    return healthy_workers, unhealthy_workers

def main():
    healthy_workers, unhealthy_workers = get_worker_status()

    if unhealthy_workers:
        print(f"CRITICAL: There are unhealthy workers {unhealthy_workers}")

    else:
        print("OK: All htcondor workers are healthy.")

if __name__ == "__main__":
    main()
