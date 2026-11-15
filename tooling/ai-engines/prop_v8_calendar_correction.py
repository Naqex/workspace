"""One source-confirmed calendar correction; never reselect the V8 composition."""
from prop_v8_common import *
from prop_v8_campaign import temporary_bindings
import hashlib

CORRECTION = Path("planning/research/PROP-V8-CALENDAR-CORRECTION-20261115.json")
CORRECTED = JOB / "calendar-corrected"


def corrected_data():
    cfg = read(CORRECTION)
    raw = CALENDAR.read_bytes()
    # The registered Windows bytes use CRLF; Git's Linux checkout uses LF.
    # Reconstruct only that representation, retaining the original frozen hash.
    windows_bytes = raw.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
    if (hashlib.sha256(raw).hexdigest() != cfg["parent_calendar_sha256"] and
            hashlib.sha256(windows_bytes).hexdigest() != cfg["parent_calendar_sha256"]):
        raise ValueError("V8_calendar_correction_parent_changed")
    data = read(CALENDAR)
    target = next(r for r in data["events"] if r["day"] == "2021-12-31")
    if target["kind"] != "CLOSED":
        raise ValueError("V8_expected_old_calendar_witness")
    target.update(kind="CONSERVATIVE_EVE", flat_utc="16:58",
        target_time_status="VERIFIED_FTMO_NORMAL_HOURS_REGISTERED_EVE_GUARD_RETAINED",
        source=cfg["official_source"])
    return data


def run(order):
    verify()
    cfg = read(CORRECTION)
    head = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    committed = subprocess.check_output(["git","show",head+":"+CORRECTION.as_posix()])
    if json.loads(committed) != cfg:
        raise ValueError("V8_calendar_fix_not_committed_before_remeasurement")
    CORRECTED.mkdir(exist_ok=True)
    path = CORRECTED / "calendar.json"
    data = corrected_data()
    if path.exists() and read(path) != data:
        raise ValueError("V8_corrected_calendar_drift")
    write_json(path,data)
    write_json(CORRECTED / "release.json",dict(commit=head,configuration_changed=False,
        correction_sha256=digest(CORRECTION),calendar_sha256=digest(path),
        prior_attempt_preserved="original backward folders",strategy_release_count=1,
        technical_attempt=2,calendar_changes=["2021-12-31 CLOSED -> registered conservative 16:58 guard"]))
    import prop_v8_source as source
    import prop_v8_campaign as campaign
    import prop_v8_review as review
    with temporary_bindings(source,dict(JOB=CORRECTED)), \
         temporary_bindings(campaign,dict(JOB=CORRECTED,CALENDAR=path)), \
         temporary_bindings(review,dict(JOB=CORRECTED,CALENDAR=path)):
        campaign.evaluate("backward",order)
        review.run("backward",order)
    event("V8_calendar_corrected_PASS",order=order,configuration_changed=False)


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--order",choices=ORDERS,default=ORDERS[0])
    run(p.parse_args().order)
