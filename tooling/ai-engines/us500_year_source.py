"""Read all four US500 quarters from an already admitted, pinned source proof."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def load_year_side(root, *, year, side, proof_sha256):
    """Proof hash must come from the accepted source receipt, not a new self-seal.

    This binds the derived canonical files; it does not rerun raw transformation
    or certify a new producer. A pilot quarter selection is never a full year.
    """
    root = Path(root)
    if (not root.is_absolute() or type(year) is not int or year not in (2019, 2022, 2023, 2024)
            or side not in ('bid', 'ask') or type(proof_sha256) is not str
            or re.fullmatch('[a-f0-9]{64}', proof_sha256) is None):
        raise ValueError('explicit_registered_year_side_and_proof_required')
    proof_path = root/'source-observation-proof.json'
    proof_bytes = proof_path.read_bytes()
    if hashlib.sha256(proof_bytes).hexdigest() != proof_sha256:
        raise ValueError('accepted_source_proof_binding')
    proof = json.loads(proof_bytes)
    expected = {f'q{q}-{s}' for q in range(1, 5) for s in ('bid', 'ask')}
    seals = proof['output_seals']
    if (proof['schema'] != 'explicit-source-M1-proof-v1'
            or proof['status'] != 'source_explicit_prices_and_pairing_verified'
            or proof['policy'] != 'paired-explicit-source-M1-v1'
            or proof['instrument'] != 'usa500idxusd' or proof['year'] != year
            or proof['holdout_read'] is not False
            or [q['quarter'] for q in proof['quarters']] != [1, 2, 3, 4]
            or len(seals) != 8 or {s['request'] for s in seals} != expected):
        raise ValueError('full_four_quarter_source_contract')
    by_name = {s['request']: s for s in seals}
    result, bindings, quarter_rows = {}, {str(proof_path): proof_sha256}, {}
    for quarter in range(1, 5):
        name = f'q{quarter}-{side}'
        path = root/(name+'.json')
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        seal = by_name[name]
        if digest != seal['sha256']:
            raise ValueError('canonical_quarter_seal')
        rows = json.loads(payload)
        if (type(rows) is not list or type(seal['rows']) is not int or len(rows) != seal['rows']
                or (rows and (rows[0]['timestamp'] != seal['first'] or rows[-1]['timestamp'] != seal['last']))):
            raise ValueError('canonical_quarter_census')
        lower = int(datetime(year, 3*quarter-2, 1, tzinfo=timezone.utc).timestamp()*1000)
        upper = int(datetime(year+1, 1, 1, tzinfo=timezone.utc).timestamp()*1000) if quarter == 4 else int(datetime(year, 3*quarter+1, 1, tzinfo=timezone.utc).timestamp()*1000)
        previous = lower-1
        for row in rows:
            at = row['timestamp']
            if type(at) is not int or not lower <= at < upper or at % 60000 or at <= previous or at in result:
                raise ValueError('canonical_quarter_clock_or_duplicate')
            result[at] = row
            previous = at
        bindings[str(path)] = digest
        quarter_rows[quarter] = len(rows)
    return dict(rows=result, bindings=bindings, quarter_rows=quarter_rows,
                scope='accepted_frozen_canonical_four_quarters_not_new_raw_validation')
