#!/usr/bin/env python3

"""
Check that rsnapshot is producing fresh snapshots and not failing.

Written for the BERDL global_share snapshots on ks1-p (DEVOPS-2908), but
works for any rsnapshot install that writes a logfile.

What it checks:
  * age of the last "<interval>: completed successfully" line in the
    rsnapshot logfile (the lowest interval, e.g. daily, is the only one that
    actually syncs data, so that is the one whose age matters)
  * whether the most recent run of ANY interval ended in ERROR (crit) or
    "completed, but with some warnings" (warn)
  * age of <snapshot_root>/<interval>.0, which rsnapshot touches after every
    successful sync (catches a log that looks fine but no new snapshot)
  * a lockfile older than --lock-hours (a run that is stuck or never ended)

Note that a weekly/monthly run with nothing to promote ("not present (yet),
nothing to copy") still logs "completed successfully". That is normal
rsnapshot behaviour and is not reported as a problem.

Nagios exit statuses (for use with mrpe):
Exits 2 if the last sync is older than --crit-hours, or the last run of any
        interval ended in ERROR, or no successful sync is found in the log
Exits 1 if the last sync is older than --warn-hours, the last run ended with
        warnings, or the lockfile is older than --lock-hours
Exits 0 otherwise
Exits 3 if the logfile can't be read

Thresholds: with "daily" running every day, the defaults (26h / 50h) fit.
If daily is skipped on the days weekly/monthly run, the normal gap is 48h
(96h at the end of February), so use e.g. --warn-hours 50 --crit-hours 98.

Example mrpe.cfg line:
rsnapshot_global_share /usr/local/bin/rsnapshot_status.py --snapshot-root /data1/backups/berdl_global_share_rsnapshot

No dependencies beyond the Python 3 standard library.
"""

import argparse
import datetime
import os
import re
import sys

OK, WARN, CRIT, UNKNOWN = 0, 1, 2, 3
STATUS_NAMES = {OK: "OK", WARN: "WARN", CRIT: "CRIT", UNKNOWN: "UNKNOWN"}

# [2026-11-16T04:33:38] /usr/bin/rsnapshot daily: completed successfully
LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s+\S*rsnapshot\s+(?P<interval>\S+):\s+(?P<msg>.*)$")


def parse_ts(ts):
    # rsnapshot logs local time, e.g. 2026-11-16T04:33:38
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%b/%Y:%H:%M:%S"):
        try:
            return datetime.datetime.strptime(ts, fmt)
        except ValueError:
            pass
    return None


def classify(msg):
    if "completed successfully" in msg:
        return "success"
    if "completed, but with some warnings" in msg:
        return "warnings"
    if "ERROR" in msg:
        return "error"
    return None


def read_events(logfile):
    """Return (timestamp, interval, outcome, msg) for every run-ending line.

    Reads the rotated plain-text log first (if present) so a freshly rotated
    log doesn't look like "no successful run".
    """
    events = []
    for path in (logfile + ".1", logfile):
        if not os.path.isfile(path):
            continue
        with open(path, errors="replace") as fh:
            for line in fh:
                m = LINE_RE.match(line.strip())
                if not m:
                    continue
                outcome = classify(m.group("msg"))
                ts = parse_ts(m.group("ts"))
                if outcome and ts:
                    events.append((ts, m.group("interval"), outcome, m.group("msg")))
    events.sort(key=lambda e: e[0])
    return events


def hours_since(then, now):
    return (now - then).total_seconds() / 3600.0


def main():
    parser = argparse.ArgumentParser(description="check_mk/mrpe check for rsnapshot")
    parser.add_argument("--logfile", default="/var/log/rsnapshot.log")
    parser.add_argument("--interval", default="daily",
                        help="lowest rsnapshot interval, the one that syncs (default: daily)")
    parser.add_argument("--snapshot-root",
                        help="snapshot_root from rsnapshot.conf; enables the <interval>.0 age check")
    parser.add_argument("--lockfile", default="/var/run/rsnapshot.pid")
    parser.add_argument("--warn-hours", type=float, default=26)
    parser.add_argument("--crit-hours", type=float, default=50)
    parser.add_argument("--lock-hours", type=float, default=20)
    args = parser.parse_args()

    now = datetime.datetime.now()

    if not os.path.isfile(args.logfile):
        print(f"UNKNOWN - rsnapshot logfile {args.logfile} not found")
        return UNKNOWN
    try:
        events = read_events(args.logfile)
    except OSError as exc:
        print(f"UNKNOWN - can't read {args.logfile}: {exc}")
        return UNKNOWN

    status = OK
    problems = []
    details = []
    age = None

    def raise_to(level, text):
        nonlocal status
        status = max(status, level)
        problems.append(text)

    # 1. age of the last successful sync ("with some warnings" still made a
    #    snapshot; the warning itself is reported in step 2)
    successes = [e for e in events if e[1] == args.interval and e[2] in ("success", "warnings")]
    if not successes:
        raise_to(CRIT, f"no successful 'rsnapshot {args.interval}' found in {args.logfile}")
    else:
        last_ok = successes[-1][0]
        age = hours_since(last_ok, now)
        details.append(f"last {args.interval} OK {last_ok:%Y-%m-%d %H:%M} ({age:.1f}h ago)")
        if age > args.crit_hours:
            raise_to(CRIT, f"last {args.interval} sync {age:.1f}h ago (> {args.crit_hours:g}h)")
        elif age > args.warn_hours:
            raise_to(WARN, f"last {args.interval} sync {age:.1f}h ago (> {args.warn_hours:g}h)")

    # 2. most recent outcome of every interval seen in the log
    last_by_interval = {}
    for ts, interval, outcome, msg in events:
        last_by_interval[interval] = (ts, outcome, msg)
    for interval, (ts, outcome, msg) in sorted(last_by_interval.items()):
        if outcome == "error":
            raise_to(CRIT, f"last {interval} run failed {ts:%Y-%m-%d %H:%M}: {msg[:120]}")
        elif outcome == "warnings":
            raise_to(WARN, f"last {interval} run had warnings {ts:%Y-%m-%d %H:%M}")

    # 3. age of <interval>.0 (rsnapshot touches it after each successful sync)
    if args.snapshot_root:
        snap0 = os.path.join(args.snapshot_root, f"{args.interval}.0")
        if not os.path.isdir(snap0):
            raise_to(CRIT, f"{snap0} does not exist")
        else:
            snap_age = hours_since(datetime.datetime.fromtimestamp(os.path.getmtime(snap0)), now)
            details.append(f"{args.interval}.0 is {snap_age:.1f}h old")
            if snap_age > args.crit_hours:
                raise_to(CRIT, f"{args.interval}.0 is {snap_age:.1f}h old (> {args.crit_hours:g}h)")
            elif snap_age > args.warn_hours:
                raise_to(WARN, f"{args.interval}.0 is {snap_age:.1f}h old (> {args.warn_hours:g}h)")

    # 4. stuck run: lockfile hanging around too long
    if os.path.exists(args.lockfile):
        lock_age = hours_since(datetime.datetime.fromtimestamp(os.path.getmtime(args.lockfile)), now)
        details.append(f"rsnapshot running for {lock_age:.1f}h")
        if lock_age > args.lock_hours:
            raise_to(WARN, f"lockfile {args.lockfile} is {lock_age:.1f}h old, run may be stuck")

    summary = "; ".join(problems) if problems else "rsnapshot OK"
    if details:
        summary += " - " + ", ".join(details)
    perf = ""
    if age is not None:
        perf = f" | last_sync_age_hours={age:.2f};{args.warn_hours:g};{args.crit_hours:g};0"
    print(f"{STATUS_NAMES[status]} - {summary}{perf}")
    return status


if __name__ == "__main__":
    sys.exit(main())
