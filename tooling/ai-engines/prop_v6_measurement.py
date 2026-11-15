"""Fail-closed measurement boundaries; frozen trading decisions are unchanged."""
from prop_v6_account import HarvestAccount


class MeasuredHarvest(HarvestAccount):
    """An unpriceable scheduled exit makes the subsequent account path unknown."""
    def measurement_limit(self):
        limits = [(self._trades[i]["deadline_msc"], i) for i in self.active
                  if self._trades[i].get("reason") == "ENDPOINT_UNKNOWN_OPEN"]
        return min(limits) if limits else None

    def censor(self, at):
        if getattr(self, "path_censor", None):
            return True
        limit = self.measurement_limit()
        if limit and at >= limit[0]:
            self.path_censor = dict(at=limit[0], trade=limit[1],
                                    reason="SCHEDULED_EXIT_HAS_NO_ADMITTED_QUOTE",
                                    last_measurement_msc=getattr(self, "last_measurement_msc", None))
            return True
        return False

    def check(self, at, floating):
        if self.censor(at) or not self.start <= at < self.end:
            return
        super().check(at, floating)

    def observe_policy(self, at, equity):
        if not self.censor(at):
            super().observe_policy(at, equity)

    def action(self, kind, at, i, trades, quote, mult=0):
        if self.censor(at):
            return
        super().action(kind, at, i, trades, quote, mult)

    def segment(self, rows, trades, cache):
        if getattr(self, "path_censor", None) or not len(rows):
            return
        limit = self.measurement_limit()
        if limit:
            cut = int(rows["t"].searchsorted(limit[0]))
            if cut < len(rows):
                if cut:
                    super().segment(rows[:cut], trades, {})
                    self.last_measurement_msc = int(rows["t"][cut - 1])
                # A harvest may have liquidated the unknown-deadline trade
                # before its deadline, so recheck whether it is still active.
                if self.censor(int(rows["t"][cut])):
                    return
                super().segment(rows[cut:], trades, {})
                self.last_measurement_msc = int(rows["t"][-1])
                return
        super().segment(rows, trades, cache)
        self.last_measurement_msc = int(rows["t"][-1])

    def dump(self):
        out = super().dump()
        witness = getattr(self, "path_censor", None)
        out.update(path_censor=witness, effective_end_msc=witness["at"] if witness else self.end,
                   requested_end_msc=self.end)
        if witness:
            out["status"] = "DATA_PATH_CENSORED"
            out["terminal_equity_scope"] = "last measurable pre-gap mark; no performance after censor"
        return out
