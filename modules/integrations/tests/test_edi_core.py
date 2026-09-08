"""
Unit tests for Core EDI Engine (modules/integrations/services/edi/edi_core.py).
Tests ANSI X12 and UN/EDIFACT tokenizers, segment parsers, builders, and round-tripping.
"""

import pytest
from modules.integrations.models.edi import EdiStandard, EdiPartnerCreate
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    EdiSegment,
    EdiTransactionSet,
    EdiFunctionalGroup,
    EdiInterchange,
    detect_edi_standard,
    parse_x12,
    parse_edifact,
    parse_edi,
    serialize_x12,
    serialize_edifact,
    serialize_edi,
    X12Builder,
    EdifactBuilder,
    EdiSyntaxError,
)


# ---------------------------------------------------------------------------
# Delimiter and Segment Tests
# ---------------------------------------------------------------------------

def test_edi_delimiters_defaults_and_partner_factory():
    x12_delims = EdiDelimiters.x12_default()
    assert x12_delims.element_separator == "*"
    assert x12_delims.segment_terminator == "~"
    assert x12_delims.subelement_separator == ">"

    edifact_delims = EdiDelimiters.edifact_default()
    assert edifact_delims.element_separator == "+"
    assert edifact_delims.segment_terminator == "'"
    assert edifact_delims.subelement_separator == ":"
    assert edifact_delims.release_character == "?"

    partner = EdiPartnerCreate(
        partner_name="Lulu Supermarket",
        partner_code="LULU-EDI",
        edi_standard="EDIFACT",
        interchange_sender_id="LULU_SND",
        interchange_receiver_id="NOVA_RCV",
        segment_terminator="'",
        element_separator="+",
        subelement_separator=":",
        release_character="?",
    )
    p_delims = EdiDelimiters.from_partner(partner)
    assert p_delims.element_separator == "+"
    assert p_delims.release_character == "?"


def test_edi_segment_manipulation():
    seg = EdiSegment("BEG", ["00", "SA", "PO-998822", "", "20260908"])
    assert seg.tag == "BEG"
    assert seg.get(1) == "00"
    assert seg.get(2) == "SA"
    assert seg.get(3) == "PO-998822"
    assert seg.get(4) == ""
    assert seg.get(5) == "20260908"
    assert seg.get(99, "DEFAULT") == "DEFAULT"

    # Modification
    seg.set_element(3, "PO-UPDATED")
    assert seg.get(3) == "PO-UPDATED"

    # Composite element manipulation
    comp_seg = EdiSegment("LIN", ["1", ["IN", "SKU-5001", "EN", "62910410001"]])
    assert comp_seg.get(1) == "1"
    assert comp_seg.get_composite(2) == ["IN", "SKU-5001", "EN", "62910410001"]
    assert comp_seg.get_component(2, 1) == "IN"
    assert comp_seg.get_component(2, 2) == "SKU-5001"
    assert comp_seg.get_component(2, 4) == "62910410001"

    comp_seg.set_component(2, 2, "SKU-9999")
    assert comp_seg.get_component(2, 2) == "SKU-9999"


# ---------------------------------------------------------------------------
# ANSI X12 Parser & Builder Tests
# ---------------------------------------------------------------------------

SAMPLE_X12_850 = (
    "ISA*00*          *00*          *ZZ*CARREFOUR_ISA  *ZZ*NOVA_DIST_ISA  *260908*1430*U*00401*000000042*0*P*>~\n"
    "GS*PO*CARREFOUR_ISA*NOVA_DIST_ISA*20260908*1430*1*X*004010~\n"
    "ST*850*0001~\n"
    "BEG*00*NE*PO-CRF-90210**20260908~\n"
    "CUR*BY*AED~\n"
    "N1*ST*Carrefour Mall of the Emirates*92*STORE-101~\n"
    "N3*Sheikh Zayed Road~\n"
    "N4*Dubai**AE~\n"
    "PO1*1*100*CA*45.50*PE*CB*6291041000101*VN*SUPP-MILK-1L~\n"
    "PID*F****Fresh Milk Full Cream 1L Case of 12~\n"
    "PO1*2*50*CA*62.00*PE*CB*6291041000202*VN*SUPP-YOG-500G~\n"
    "PID*F****Greek Style Natural Yogurt 500g Case of 6~\n"
    "CTT*2*150~\n"
    "SE*13*0001~\n"
    "GE*1*1~\n"
    "IEA*1*000000042~"
)


def test_parse_x12_850():
    interchange = parse_x12(SAMPLE_X12_850)
    assert interchange.standard == "ANSI_X12"
    assert interchange.sender_id == "CARREFOUR_ISA"
    assert interchange.receiver_id == "NOVA_DIST_ISA"
    assert interchange.control_number == "000000042"
    assert interchange.is_test is False

    assert len(interchange.groups) == 1
    group = interchange.groups[0]
    assert group.functional_code == "PO"

    assert len(group.transactions) == 1
    tx = group.transactions[0]
    assert tx.doc_type == "850"
    assert tx.control_number == "0001"

    beg = tx.find_first("BEG")
    assert beg is not None
    assert beg.get(3) == "PO-CRF-90210"

    po1_segs = tx.find_segments("PO1")
    assert len(po1_segs) == 2
    assert po1_segs[0].get(2) == "100"  # Qty
    assert po1_segs[0].get(3) == "CA"   # UOM
    assert po1_segs[0].get(4) == "45.50"# Unit Price
    assert po1_segs[0].get(7) == "6291041000101" # Buyer GTIN

    # Loop extraction
    po1_loops = tx.get_loops("PO1", stop_tags=["CTT", "SE"])
    assert len(po1_loops) == 2
    assert len(po1_loops[0]) == 2
    assert po1_loops[0][0].tag == "PO1"
    assert po1_loops[0][1].tag == "PID"


def test_x12_builder_and_roundtrip():
    builder = X12Builder(
        sender_id="NOVA_DIST_ISA",
        receiver_id="CARREFOUR_ISA",
        sender_qualifier="ZZ",
        receiver_qualifier="ZZ",
        control_number="000000100",
    )
    builder.start_group("SH", group_control_number="1")
    builder.start_transaction("856", control_number="0001")
    builder.add_segment("BSN", "00", "ASN-2026-0099", "20260908", "1500")
    builder.add_segment("HL", "1", "", "S")
    builder.add_segment("TD1", "PLT90", "2")
    builder.add_segment("HL", "2", "1", "O")
    builder.add_segment("PRF", "PO-CRF-90210")
    builder.add_segment("HL", "3", "2", "T")
    builder.add_segment("MAN", "GM", "00362910410000000018")
    builder.end_transaction()
    builder.end_group()

    raw_x12 = builder.build()
    assert "ISA*00*" in raw_x12
    assert "GS*SH*" in raw_x12
    assert "ST*856*0001~" in raw_x12
    assert "BSN*00*ASN-2026-0099*20260908*1500~" in raw_x12
    assert "MAN*GM*00362910410000000018~" in raw_x12
    assert "GE*1*1~" in raw_x12
    assert "IEA*1*000000100~" in raw_x12

    # Parse it back
    parsed = parse_x12(raw_x12)
    assert parsed.sender_id == "NOVA_DIST_ISA"
    assert parsed.receiver_id == "CARREFOUR_ISA"
    tx = parsed.all_transactions()[0]
    assert tx.doc_type == "856"
    assert tx.find_first("BSN").get(2) == "ASN-2026-0099"
    assert tx.find_first("MAN").get(2) == "00362910410000000018"


# ---------------------------------------------------------------------------
# UN/EDIFACT Parser & Builder Tests
# ---------------------------------------------------------------------------

SAMPLE_EDIFACT_ORDERS = (
    "UNA:+.? '\n"
    "UNB+UNOA:2+LULU_HYPER:ZZ+NOVA_DIST:ZZ+260908:1430+1001'\n"
    "UNH+MSG001+ORDERS:D:96A:UN:EAN008'\n"
    "BGM+220+PO-LULU-88401+9'\n"
    "DTM+137:20260908:102'\n"
    "NAD+BY+LULU-HQ::9'\n"
    "NAD+DP+LULU-STORE-05::9++Lulu Hypermarket Al Barsha+Dubai++AE'\n"
    "LIN+1++6291041000101:SRV'\n"
    "PIA+1+SUPP-MILK-1L:IN'\n"
    "QTY+21:200:KGM'\n"
    "MOA+203:9100.00:AED'\n"
    "LIN+2++6291041000202:SRV'\n"
    "QTY+21:100:KGM'\n"
    "MOA+203:6200.00:AED'\n"
    "UNS+S'\n"
    "CNT+2:2'\n"
    "UNT+14+MSG001'\n"
    "UNZ+1+1001'"
)


def test_parse_edifact_orders():
    interchange = parse_edifact(SAMPLE_EDIFACT_ORDERS)
    assert interchange.standard == "EDIFACT"
    assert interchange.sender_id == "LULU_HYPER"
    assert interchange.receiver_id == "NOVA_DIST"
    assert interchange.control_number == "1001"

    msgs = interchange.all_transactions()
    assert len(msgs) == 1
    msg = msgs[0]
    assert msg.doc_type == "ORDERS"
    assert msg.control_number == "MSG001"

    bgm = msg.find_first("BGM")
    assert bgm is not None
    assert bgm.get(2) == "PO-LULU-88401"

    # Line item loops
    lin_loops = msg.get_loops("LIN", stop_tags=["UNS", "CNT", "UNT"])
    assert len(lin_loops) == 2
    assert lin_loops[0][0].tag == "LIN"
    assert lin_loops[0][0].get_component(3, 1) == "6291041000101"


def test_edifact_escaping_and_builder():
    builder = EdifactBuilder(
        sender_id="NOVA_DIST",
        receiver_id="LULU_HYPER",
        control_number="5002",
        include_una=True,
    )
    builder.start_message("DESADV", control_number="DES001")
    builder.add_segment("BGM", "351", "DESADV-9901", "9")
    # Test special characters requiring escape: ?, +, :, '
    builder.add_segment("FTX", "AAI", "", "", "Quality: Grade A+ & Super? Fast Delivery's Note")
    builder.end_message()

    raw_edi = builder.build()
    assert "UNA:+.? '" in raw_edi
    assert "UNB+UNOA:2+NOVA_DIST:ZZ+LULU_HYPER:ZZ+" in raw_edi
    assert "BGM+351+DESADV-9901+9'" in raw_edi
    # Verify escaped characters in FTX
    assert "Quality?: Grade A?+ & Super?? Fast Delivery?'s Note" in raw_edi

    # Round trip parse and unescape
    parsed = parse_edifact(raw_edi)
    msg = parsed.all_transactions()[0]
    ftx = msg.find_first("FTX")
    assert ftx is not None
    assert ftx.get(4) == "Quality: Grade A+ & Super? Fast Delivery's Note"


# ---------------------------------------------------------------------------
# Universal Parser & Standard Detection Tests
# ---------------------------------------------------------------------------

def test_detect_edi_standard():
    assert detect_edi_standard(SAMPLE_X12_850) == EdiStandard.ANSI_X12
    assert detect_edi_standard(SAMPLE_EDIFACT_ORDERS) == EdiStandard.EDIFACT
    assert detect_edi_standard("UNB+UNOA:2+A+B+260908:1200+1'") == EdiStandard.EDIFACT
    assert detect_edi_standard("ISA*00*          *00*") == EdiStandard.ANSI_X12


def test_universal_parse_and_serialize():
    interchange_x12 = parse_edi(SAMPLE_X12_850)
    assert interchange_x12.standard == "ANSI_X12"
    serialized_x12 = serialize_edi(interchange_x12)
    assert "ISA*00*" in serialized_x12

    interchange_edifact = parse_edi(SAMPLE_EDIFACT_ORDERS)
    assert interchange_edifact.standard == "EDIFACT"
    serialized_edifact = serialize_edi(interchange_edifact)
    assert "UNB+UNOA:2+" in serialized_edifact


def test_syntax_errors():
    with pytest.raises(EdiSyntaxError):
        parse_x12("")

    with pytest.raises(EdiSyntaxError):
        parse_edifact("")

    with pytest.raises(EdiSyntaxError):
        parse_x12("INVALID_TAG*1*2~")

    # SE without ST
    with pytest.raises(EdiSyntaxError):
        parse_x12("ISA*00*          *00*          *ZZ*A              *ZZ*B              *260908*1200*U*00401*000000001*0*P*>~SE*2*0001~")


def test_multi_transaction_x12():
    builder = X12Builder(
        sender_id="SENDER_X12",
        receiver_id="RECEIVER_X12",
        control_number="000000777",
    )
    builder.start_group("IN", group_control_number="1")
    # First 810 Invoice
    builder.start_transaction("810", control_number="0001")
    builder.add_segment("BIG", "20260908", "INV-1001", "20260908", "PO-501")
    builder.add_segment("IT1", "1", "10", "EA", "25.00", "", "VN", "PROD-A")
    builder.add_segment("TDS", "25000")
    builder.end_transaction()

    # Second 810 Invoice
    builder.start_transaction("810", control_number="0002")
    builder.add_segment("BIG", "20260908", "INV-1002", "20260908", "PO-502")
    builder.add_segment("IT1", "1", "5", "EA", "100.00", "", "VN", "PROD-B")
    builder.add_segment("TDS", "50000")
    builder.end_transaction()
    builder.end_group()

    raw_x12 = builder.build()
    parsed = parse_x12(raw_x12)
    assert len(parsed.groups) == 1
    assert len(parsed.groups[0].transactions) == 2
    txs = parsed.all_transactions()
    assert len(txs) == 2
    assert txs[0].doc_type == "810"
    assert txs[0].control_number == "0001"
    assert txs[0].find_first("BIG").get(2) == "INV-1001"
    assert txs[1].doc_type == "810"
    assert txs[1].control_number == "0002"
    assert txs[1].find_first("BIG").get(2) == "INV-1002"


def test_multi_message_edifact():
    builder = EdifactBuilder(
        sender_id="SENDER_EDI",
        receiver_id="RECEIVER_EDI",
        control_number="999",
    )
    # Message 1
    builder.start_message("INVOIC", control_number="INV01")
    builder.add_segment("BGM", "380", "INV-9001", "9")
    builder.add_segment("MOA", ["77", "1500.00", "AED"])
    builder.end_message()

    # Message 2
    builder.start_message("INVOIC", control_number="INV02")
    builder.add_segment("BGM", "380", "INV-9002", "9")
    builder.add_segment("MOA", ["77", "3200.00", "AED"])
    builder.end_message()

    raw_edi = builder.build()
    parsed = parse_edifact(raw_edi)
    msgs = parsed.all_transactions()
    assert len(msgs) == 2
    assert msgs[0].doc_type == "INVOIC"
    assert msgs[0].control_number == "INV01"
    assert msgs[0].find_first("BGM").get(2) == "INV-9001"
    assert msgs[1].doc_type == "INVOIC"
    assert msgs[1].control_number == "INV02"
    assert msgs[1].find_first("BGM").get(2) == "INV-9002"


def test_custom_delimiters():
    # Test EDIFACT with custom UNA delimiters: UNA:!./ '
    custom_edifact = (
        "UNA:!./ '\n"
        "UNB!UNOA:2!SENDER:ZZ!RECEIVER:ZZ!260908:1200!10'\n"
        "UNH!1!ORDERS:D:96A:UN:EAN008'\n"
        "BGM!220!PO-CUSTOM!9'\n"
        "UNT!4!1'\n"
        "UNZ!1!10'"
    )
    parsed = parse_edifact(custom_edifact)
    assert parsed.delimiters.element_separator == "!"
    assert parsed.delimiters.subelement_separator == ":"
    assert parsed.delimiters.decimal_mark == "."
    assert parsed.delimiters.release_character == "/"
    assert parsed.delimiters.segment_terminator == "'"

    msg = parsed.all_transactions()[0]
    assert msg.doc_type == "ORDERS"
    assert msg.find_first("BGM").get(2) == "PO-CUSTOM"

