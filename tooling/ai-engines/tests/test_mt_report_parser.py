import json
import unittest
from quant_core.mt_report_parser import preset_bytes,report_bytes,number
from quant_core.bot_lab import inspect_bytes,log_rows,fingerprint


def table(rows):
    return ("<table>"+"".join("<tr>"+"".join("<td>"+str(c)+"</td>" for c in row)+"</tr>"
                             for row in rows)+"</table>").encode()


def mt4():
    return table([["Symbol:","EURUSD"],["Period:","H1"],["Inputs:","SL=200; Password=never-print"],
        ["Open Time","Type","Size","Price","S/L","T/P","Close Time","Price","Commission","Swap","Profit"],
        ["2023.01.03 08:00:00","buy","0.10","1.06000","1.05800","1.06200",
         "2023.01.03 10:00:00","1.06200","-0.70","0.00","20.00"]])


def mt5(position=True,partial=False):
    headers=["Time","Deal","Symbol","Type","Direction","Volume","Price","Commission","Swap","Profit"]
    a=["2023.01.03 08:00:00","1","EURUSD","buy","in","0.10","1.06000","-0.35","0","0"]
    b=["2023.01.03 10:00:00","2","EURUSD","sell","out","0.05" if partial else "0.10",
       "1.06200","-0.35","0","20"]
    if position:
        headers.append("Position ID");a.append("42");b.append("42")
    return table([headers,a,b])


class PresetTests(unittest.TestCase):
    def test_mt5_current_and_optimization_bounds_are_separate(self):
        row=preset_bytes(b"SL=200||100||10||400||Y",".set")["parameters"][0]
        self.assertEqual([row[k] for k in ("value","start","step","stop","optimize")],
                         ["200","100","10","400","Y"])

    def test_mt4_separate_optimization_fields_are_grouped(self):
        rows=preset_bytes(b"SL=200\nSL,F=1\nSL,1=100\nSL,2=10\nSL,3=400",".set")["parameters"]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["optimize"],"1")
        self.assertEqual(rows[0]["stop"],"400")

    def test_ini_credentials_and_license_values_never_escape(self):
        result=preset_bytes(b"[Tester]\nLogin=1234567\nPassword=never-print\nLicenseKey=private-license\nSymbol=EURUSD",".ini")
        serialized=json.dumps(result)
        for hidden in ("1234567","never-print","private-license"):
            self.assertNotIn(hidden,serialized)
        self.assertIn("EURUSD",serialized)

    def test_chr_tags_do_not_execute_or_hide_parameters(self):
        r=inspect_bytes(b"<chart>\nperiod=60\nSL=200\n</chart>",".chr")
        self.assertEqual(len(r["parameters"]),2)
        self.assertFalse(r["execution_performed"])

    def test_utf16_and_unrecognized_tuple_are_retained_as_review(self):
        result=preset_bytes("SL=200||100".encode("utf-16"),".set")
        self.assertEqual(result["parameters"][0]["tuple_status"],"UNRECOGNIZED_OPTIMIZATION_ARITY")

    def test_preset_values_are_never_evaluated(self):
        row=preset_bytes(b"x=__import__('untrusted_module')",".set")["parameters"][0]
        self.assertEqual(row["value"],"__import__('untrusted_module')")


class TesterReportTests(unittest.TestCase):
    def test_mt4_closed_table_headers_costs_and_metadata(self):
        r=report_bytes(mt4(),".htm")
        self.assertTrue(r["clone_ready"])
        self.assertEqual(r["header"]["Period"],"H1")
        self.assertNotIn("never-print",json.dumps(r))
        self.assertAlmostEqual(r["trades"][0]["profit"],19.3)
        self.assertEqual(r["trades"][0]["open_time"],"2023-01-03 08:00:00")

    def test_native_report_flows_into_existing_cloner(self):
        rows=log_rows(mt4(),".htm")
        with self.assertRaisesRegex(ValueError,"LOG_TIMEZONE_REQUIRED"):
            fingerprint(rows)
        r=fingerprint(rows,timezone_name="UTC")
        self.assertEqual(r["trades"],1)
        self.assertFalse(r["algorithm_identifiable"])

    def test_mt5_position_pairing_preserves_entry_and_exit_costs(self):
        r=report_bytes(mt5(),".html")
        self.assertTrue(r["clone_ready"])
        self.assertAlmostEqual(r["trades"][0]["profit"],19.3)
        self.assertEqual(r["trades"][0]["side"],"BUY")

    def test_mt5_missing_position_identity_is_not_guessed_from_order(self):
        r=report_bytes(mt5(position=False),".html")
        self.assertFalse(r["clone_ready"])
        self.assertIn("DEAL_POSITION_ID_REQUIRED",r["warnings"])
        with self.assertRaisesRegex(ValueError,"PAIRING"):
            log_rows(mt5(position=False),".html")

    def test_partial_volume_is_not_reported_as_a_complete_trade(self):
        r=report_bytes(mt5(partial=True),".html")
        self.assertFalse(r["clone_ready"])
        self.assertIn("DEAL_PAIR_INCOMPLETE",r["warnings"])

    def test_xml_spreadsheet_rows_reuse_same_canonicalization(self):
        headers=["OpenTime","CloseTime","Type","Volume","Price","Symbol","Profit"]
        row=["2023.01.03 08:00","2023.01.03 10:00","sell",".10","1.06000","EURUSD","2"]
        row[3]="0.10"
        xml="<Workbook><Table>"+"".join("<Row>"+"".join("<Cell><Data>"+v+"</Data></Cell>" for v in values)+"</Row>"
                                      for values in (headers,row))+"</Table></Workbook>"
        r=report_bytes(xml.encode(),".xml")
        self.assertTrue(r["clone_ready"])
        self.assertEqual(len(log_rows(xml.encode(),".xml")),1)

    def test_xml_entities_are_blocked_before_parsing(self):
        raw=b'<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///never-read">]><x>&xxe;</x>'
        with self.assertRaisesRegex(ValueError,"DOCTYPE"):
            report_bytes(raw,".xml")

    def test_ambiguous_localized_and_nonfinite_numbers_are_rejected(self):
        for value in ("1,234","NaN","inf","1e9"):
            with self.assertRaises(ValueError):number(value)

    def test_non_report_html_is_review_evidence_not_a_clone(self):
        r=report_bytes(b"<html><p>Marketing report</p></html>",".html")
        self.assertEqual(r["recognized_tables"],0)
        self.assertFalse(r["clone_ready"])

    def test_oversize_inputs_fail_before_html_or_xml_parsing(self):
        with self.assertRaisesRegex(ValueError,"SIZE_LIMIT"):
            report_bytes(b"x"*(16*1024*1024+1),".html")
