#!/usr/bin/env python

import htcondor

def get_worker_status():
    coll = htcondor.Collector()
    ads = coll.query(htcondor.AdTypes.Startd, projection=["Name", "NodeIsHealthy"])

    healthy_workers = []
    unhealthy_workers = []

    for ad in ads:
        name = ad.get('Name', 'Unknown')
        is_healthy = ad.get('NodeIsHealthy', False)

        if is_healthy:
            healthy_workers.append(name)
        else:
            unhealthy_workers.append(name)

    return healthy_workers, unhealthy_workers

def main():
    healthy_workers, unhealthy_workers = get_worker_status()

    print("Healthy Workers:")
    for worker in healthy_workers:
        print(worker)

    print("\nUnhealthy Workers:")
    for worker in unhealthy_workers:
        print(worker)

    # Determine if the situation is critical
    if unhealthy_workers:
        print("\nCRITICAL: There are unhealthy workers!")

    else:
        print("\nOK: All htcondor workers are healthy.")

if __name__ == "__main__":
    main()
