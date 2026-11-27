"""Bounded MT presets and tester tables; never execute settings or infer a strategy."""

import hashlib
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

PRESETS = {".set", ".ini", ".chr"}
REPORTS = {".htm", ".html", ".xml"}
LIMIT = 16 * 1024 * 1024
SENSITIVE = re.compile(r"password|passwd|secret|token|api.?key|login|account|server|private.?key|license.?key", re.I)
ALIASES = {
    "opentime": "open_time",
    "closetime": "close_time",
    "symbol": "symbol",
    "type": "side",
    "size": "volume",
    "volume": "volume",
    "price": "price",
    "openprice": "price",
    "closeprice": "close_price",
    "sl": "sl",
    "stoploss": "sl",
    "initialsl": "initial_sl",
    "initialstoploss": "initial_sl",
    "tp": "tp",
    "takeprofit": "tp",
    "profit": "profit",
    "netprofit": "net_profit",
    "commission": "commission",
    "swap": "swap",
    "fee": "fee",
    "taxes": "tax",
    "tax": "tax",
    "time": "time",
    "deal": "deal",
    "order": "order",
    "ticket": "ticket",
    "direction": "direction",
    "position": "position",
    "positionid": "position",
    "state": "state",
}
HEADERS = {
    "symbol": "Symbol",
    "period": "Period",
    "inputs": "Inputs",
    "parameters": "Inputs",
    "barsintest": "Bars in test",
    "bars": "Bars in test",
    "ticksmodelled": "Ticks modelled",
    "ticks": "Ticks modelled",
    "modellingquality": "Modelling quality",
    "modelingquality": "Modelling quality",
    "historyquality": "Modelling quality",
}


def key(text):
    return re.sub(r"[^a-z0-9]", "", str(text).casefold())


def decode(raw):
    if len(raw) > LIMIT:
        raise ValueError("MT_INPUT_SIZE_LIMIT_16MIB")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        declared = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", raw[:4096], re.I)
        encoding = declared[1].decode("ascii").casefold() if declared else "windows-1252"
        if encoding not in {"windows-1252", "windows-1251", "iso-8859-1"}:
            raise ValueError("MT_REPORT_ENCODING_UNSUPPORTED") from None
        return raw.decode(encoding)


def safe_value(name, value):
    return "[REDACTED]" if SENSITIVE.search(name) or SENSITIVE.search(value) else value[:4096]


def preset_bytes(raw, suffix):
    text = decode(raw)
    parameters = {}
    section = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith((";", "#", "//", "<")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1][:128]
            continue
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()[:128]
        value = value.strip()
        mt4 = re.fullmatch(r"(.+),([F123])", name)
        if mt4:
            name, part = mt4.groups()
            row = parameters.setdefault((section, name), dict(name=name, section=section))
            label = {"F": "optimize", "1": "start", "2": "step", "3": "stop"}[part]
            row[label] = safe_value(name, value)
            row["format"] = "MT4_SEPARATE_FIELDS"
            continue
        parts = value.split("||")
        row = parameters.setdefault((section, name), dict(name=name, section=section))
        row.update(
            value=safe_value(name, parts[0]), format="MT5_OPTIMIZATION_TUPLE" if len(parts) == 5 else "KEY_VALUE"
        )
        if len(parts) == 5:
            row.update(
                {
                    label: safe_value(name, item)
                    for label, item in zip(("start", "step", "stop", "optimize"), parts[1:], strict=True)
                }
            )
        elif len(parts) > 1:
            row["tuple_status"] = "UNRECOGNIZED_OPTIMIZATION_ARITY"
    rows = list(parameters.values())
    return dict(
        schema="BotPresetProfile-v1",
        sha256=hashlib.sha256(raw).hexdigest(),
        format=suffix,
        parameters=rows,
        units="UNDECLARED_UNLESS_SYMBOL_DIGITS_AND_PARAMETER_CONTRACT_EXIST",
        findings=[dict(flag="PRESET_NOT_EXECUTION_OR_ALPHA_PROOF")],
        execution_performed=False,
        admission="REVIEW_REQUIRED",
    )


def number(value):
    value = str(value).replace("\xa0", "").replace(" ", "").strip()
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        raise ValueError("AMBIGUOUS_OR_INVALID_REPORT_NUMBER")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("NONFINITE_REPORT_NUMBER")
    return result


def timestamp(value):
    value = str(value).strip()
    if re.fullmatch(r"\d{4}\.\d\d\.\d\d \d\d:\d\d(?::\d\d)?", value):
        return value[:10].replace(".", "-") + value[10:]
    return value


def canonical(row, header):
    required = ("open_time", "close_time", "volume", "price")
    if any(not row.get(k) for k in required):
        raise ValueError("CLOSED_TRADE_GEOMETRY_REQUIRED")
    side = str(row.get("side", "")).casefold()
    if side not in {"buy", "sell"}:
        raise ValueError("NON_TRADE_ROW")
    symbol = row.get("symbol") or header.get("Symbol", "").split(" ")[0]
    if not symbol or not re.fullmatch(r"[\w.+#-]{1,40}", symbol):
        raise ValueError("REPORT_SYMBOL_REQUIRED")
    volume, price = number(row["volume"]), number(row["price"])
    if volume <= 0 or price <= 0:
        raise ValueError("INVALID_REPORT_TRADE_GEOMETRY")
    net = (
        number(row["net_profit"])
        if row.get("net_profit")
        else (number(row["profit"]) + sum(number(row.get(k) or "0") for k in ("commission", "swap", "fee", "tax")))
    )
    open_time, close_time = timestamp(row["open_time"]), timestamp(row["close_time"])
    if datetime.fromisoformat(close_time) < datetime.fromisoformat(open_time):
        raise ValueError("REPORT_CLOSE_PRECEDES_ENTRY")

    def observed(name):
        if row.get(name) in (None, ""):
            return None
        try:
            return float(number(row[name]))
        except ValueError:
            return None

    audit_net = (
        float(net)
        if row.get("net_profit") or all(row.get(k) not in (None, "") for k in ("profit", "commission", "swap"))
        else None
    )
    return dict(
        symbol=symbol,
        side=side.upper(),
        open_time=open_time,
        close_time=close_time,
        volume=float(volume),
        price=float(price),
        sl=float(number(row.get("sl") or "0")),
        tp=float(number(row.get("tp") or "0")),
        profit=float(net),
        profit_scope="net from reported signed costs",
        timezone_inferred=False,
        close_price=observed("close_price"),
        audit_sl=observed("sl"),
        audit_tp=observed("tp"),
        audit_initial_sl=observed("initial_sl"),
        gross_profit=observed("profit"),
        commission=observed("commission"),
        swap=observed("swap"),
        fee=observed("fee"),
        audit_net_profit=audit_net if row.get("audit_costs_complete", True) else None,
    )


def table_records(headers, rows):
    names = []
    seen = defaultdict(int)
    for value in headers:
        normalized = ALIASES.get(key(value), "")
        seen[normalized] += 1
        if normalized == "price" and seen[normalized] > 1:
            normalized = "close_price"
        if normalized == "time" and seen[normalized] > 1:
            normalized = "end_time"
        names.append(normalized)
    output = []
    for row in rows:
        if len(row) != len(names):
            break
        value = {name: safe_value(name, item) for name, item in zip(names, row, strict=True) if name}
        if value:
            output.append(value)
    return output


def mt4_operations(records, header, warnings):
    """Pair an MT4 tester operation only with its own unambiguous order ticket."""
    pending = defaultdict(list)
    closed = []
    entries = {"buy", "sell"}
    exits = {"close", "s/l", "t/p", "close at stop", "stop loss", "take profit"}
    for row in records:
        side, ticket = row.get("side", "").casefold(), row.get("order")
        if side not in entries | exits:
            continue
        if not ticket:
            warnings.append("MT4_ORDER_TICKET_REQUIRED")
            continue
        if side in entries:
            pending[ticket].append(row)
            continue
        candidates = pending.pop(ticket, [])
        if len(candidates) != 1:
            warnings.append("MT4_ORDER_PAIRING_INCOMPLETE")
            continue
        entry = candidates[0]
        try:
            if number(entry["volume"]) != number(row["volume"]):
                raise ValueError("MT4_PARTIAL_CLOSE")
            report = dict(entry, open_time=entry["time"], close_time=row["time"], close_price=row.get("price"))
            report.update(
                {
                    name: row[name]
                    for name in ("profit", "net_profit", "commission", "swap", "tax", "fee")
                    if row.get(name)
                }
            )
            closed.append(canonical(report, header))
        except (KeyError, ValueError, TypeError):
            warnings.append("MT4_ORDER_PAIRING_INCOMPLETE")
    if pending:
        warnings.append("MT4_OPEN_OR_PARTIAL_ORDERS")
    return closed


def extract_rows(raw, suffix):
    text = decode(raw)
    if suffix == ".xml":
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
            raise ValueError("XML_ENTITIES_OR_DOCTYPE_FORBIDDEN")
        root = ET.fromstring(text)
        rows = []
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].casefold() == "row":
                rows.append(["".join(cell.itertext()).strip() for cell in node])
        if not rows:
            groups = defaultdict(list)
            for node in root.iter():
                kind = node.tag.rsplit("}", 1)[-1].casefold()
                if kind in ("trade", "deal", "order") and list(node):
                    groups[kind].append({c.tag.rsplit("}", 1)[-1]: "".join(c.itertext()) for c in node})
            for values in groups.values():
                columns = list(values[0])
                rows += [columns] + [[v.get(k, "") for k in columns] for v in values]
        metadata = {
            HEADERS[key(n.tag.rsplit("}", 1)[-1])]: (n.text or "").strip()
            for n in root.iter()
            if key(n.tag.rsplit("}", 1)[-1]) in HEADERS and not list(n)
        }
    else:
        from quant_core.bot_lab import Tables

        class BoundedTables(Tables):
            def handle_endtag(self, tag):
                super().handle_endtag(tag)
                if len(self.rows) > 50010:
                    raise ValueError("MT_REPORT_ROW_LIMIT")

            def handle_data(self, data):
                if len(data) > 65536:
                    raise ValueError("MT_REPORT_CELL_LIMIT")
                super().handle_data(data)

        parser = BoundedTables()
        parser.feed(text)
        rows = parser.rows
        metadata = {}
    if len(rows) > 50010 or any(len(row) > 128 for row in rows):
        raise ValueError("MT_REPORT_TABLE_LIMIT")
    return rows, metadata


def report_bytes(raw, suffix):
    rows, metadata = extract_rows(raw, suffix)
    for row in rows:
        for i, cell in enumerate(row[:-1]):
            label = HEADERS.get(key(cell.rstrip(":")))
            if label and row[i + 1]:
                metadata.setdefault(label, row[i + 1])
    header = {}
    for label, value in metadata.items():
        if label == "Inputs":
            header[label] = preset_bytes(str(value).replace(";", "\n").encode(), ".set")["parameters"]
        else:
            header[label] = safe_value(label, str(value))
    orders = []
    deals = []
    closed = []
    warnings = []
    recognised = 0
    for i, row in enumerate(rows):
        keys = {ALIASES.get(key(x), "") for x in row}
        columns = [ALIASES.get(key(x), "") for x in row]
        positions_layout = columns.count("time") == 2 and {"side", "volume", "price", "profit"} <= keys
        kind = (
            "closed"
            if {"open_time", "close_time", "volume", "price"} <= keys or positions_layout
            else "deals"
            if {"deal", "direction", "volume", "price", "time"} <= keys
            else "orders"
            if {"order", "state", "volume"} <= keys
            else "mt4_operations"
            if {"order", "side", "time", "volume", "price", "profit"} <= keys
            else None
        )
        if kind is None:
            continue
        recognised += 1
        records = table_records(row, rows[i + 1 :])
        if kind == "closed":
            for record in records:
                if record.get("side", "").casefold() not in ("buy", "sell"):
                    continue
                if positions_layout:
                    record.update(open_time=record.get("time"), close_time=record.get("end_time"))
                try:
                    closed.append(canonical(record, header))
                except (ValueError, KeyError, TypeError):
                    warnings.append("CLOSED_ROW_INCOMPLETE")
        elif kind == "deals":
            deals.extend(records)
        elif kind == "mt4_operations":
            orders.extend(records)
            closed.extend(mt4_operations(records, header, warnings))
        else:
            orders.extend(records)
    positions = defaultdict(list)
    for row in deals if not closed else ():
        if row.get("side", "").casefold() not in ("buy", "sell"):
            continue
        if not row.get("position"):
            warnings.append("DEAL_POSITION_ID_REQUIRED")
            continue
        positions[row["position"]].append(row)
    for values in positions.values():
        if len(values) != 2 or {r.get("direction", "").casefold() for r in values} != {"in", "out"}:
            warnings.append("PARTIAL_OR_REVERSAL_PAIRING_UNSUPPORTED")
            continue
        entry = next(r for r in values if r["direction"].casefold() == "in")
        exit = next(r for r in values if r["direction"].casefold() == "out")
        try:
            if (
                number(entry["volume"]) != number(exit["volume"])
                or entry["side"].casefold() == exit["side"].casefold()
                or entry.get("symbol") != exit.get("symbol")
            ):
                raise ValueError("DEAL_PAIR_MISMATCH")
            components = {
                k: str(sum(number(r[k]) for r in values))
                for k in ("profit", "commission", "swap", "fee")
                if all(r.get(k) not in (None, "") for r in values)
            }
            row = dict(
                entry,
                open_time=entry["time"],
                close_time=exit["time"],
                close_price=exit["price"],
                net_profit=str(
                    sum(number(r.get(k) or "0") for r in values for k in ("profit", "commission", "swap", "fee"))
                ),
                audit_costs_complete=all(k in components for k in ("profit", "commission", "swap")),
            )
            row.update({k: components.get(k) for k in ("profit", "commission", "swap", "fee")})
            closed.append(canonical(row, header))
        except (KeyError, ValueError, TypeError):
            warnings.append("DEAL_PAIR_INCOMPLETE")
    return dict(
        schema="MTTesterReport-v1",
        sha256=hashlib.sha256(raw).hexdigest(),
        format=suffix,
        header=header,
        orders=orders,
        deals=deals,
        trades=closed,
        recognized_tables=recognised,
        warnings=sorted(set(warnings)),
        clone_ready=bool(closed) and not warnings,
        timezone="EXPLICIT_CALLER_TIMEZONE_REQUIRED_FOR_NAIVE_TIMES",
        findings=[dict(flag="OBSERVED_REPORT_NOT_CAUSAL_ALPHA")],
        execution_performed=False,
        admission="OBSERVED_LOG_REPLAY_ONLY" if closed and not warnings else "REPORT_REVIEW_REQUIRED",
    )
