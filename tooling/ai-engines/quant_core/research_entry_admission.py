"""Opt-in entry admission for explicitly registered research hard-flat windows."""


def hard_flat_entry_rejection(decision_msc, quote_msc, windows):
    """Return the rejection reason for an intent spanning a closed window.

    Windows are pairs of cutoff and reopen timestamps. A missing reopen
    means the caller has yet to establish an end to the closure. The quote
    can be absent so a decision within a closure still gets a calendar reason.
    Market observations and exit-only calendar clamps do not define windows.
    """
    last_msc = decision_msc if quote_msc is None else quote_msc
    if last_msc < decision_msc:
        raise ValueError("entry_quote_precedes_decision")
    for flat_msc, reopen_msc in windows:
        if reopen_msc is not None and reopen_msc <= flat_msc:
            raise ValueError("invalid_hard_flat_window")
        if last_msc < flat_msc or (reopen_msc is not None and decision_msc >= reopen_msc):
            continue
        if reopen_msc is None:
            return "HARD_FLAT_REOPEN_UNKNOWN"
        if decision_msc >= flat_msc:
            return "DECISION_IN_HARD_FLAT_WINDOW"
        return "ENTRY_QUOTE_CROSSES_HARD_FLAT"
    return None
