"""Dry-run polls against the live registry (reads only), with the poller's clock
set to each daily 05:00Z CronJob run from 2026-09-30 to 2026-10-08.

argv[1]: the version-poller app dir to import. The registry is read once (live)
and cached for the later clock settings. Jenkins is a stub that is never
building; no trigger state (each poll is judged alone), no depends checkers.
"""
import logging, sys
from datetime import datetime, timedelta, timezone
import requests
sys.path.insert(0, sys.argv[1])
import poller as poller_mod
from poller import RegistryTimerPoller
from registry import Registry

class Cached:
    def __init__(self, reg): self.reg, self.t, self.l = reg, {}, {}
    def catalog(self):
        if "c" not in self.t: self.t["c"] = self.reg.catalog()
        return self.t["c"]
    def tags(self, repo):
        if repo not in self.t: self.t[repo] = self.reg.tags(repo)
        return self.t[repo]
    def config_labels(self, repo, tag):
        if (repo, tag) not in self.l: self.l[(repo, tag)] = self.reg.config_labels(repo, tag)
        return self.l[(repo, tag)]

class NeverBuilding:
    def is_building_or_queued(self, name): return False
    def trigger(self, name, params=None): raise AssertionError("dry run triggered")

class Clock(datetime):
    at = None
    @classmethod
    def now(cls, tz=None): return cls.at

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
reg = Cached(Registry(requests.Session(), "http://registry:5000"))
poller_mod.datetime = Clock
for day in range(30, 39):
    Clock.at = datetime(2026, 9, 1, 5, 0, tzinfo=timezone.utc) + timedelta(days=day - 1)
    logging.info("=== poll at %s", Clock.at.isoformat())
    triggered = RegistryTimerPoller(reg, NeverBuilding(), timedelta(days=14), dry_run=True).run()
    logging.info("=== %s would trigger %s", Clock.at.date(), sorted(triggered))
