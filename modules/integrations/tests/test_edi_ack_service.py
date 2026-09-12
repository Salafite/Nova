"""
Unit tests for Functional Acknowledgment Generation & Interpretation Service
(modules/integrations/services/edi/edi_ack_service.py).
Tests ANSI X12 997 FA and UN/EDIFACT CONTRL acknowledgment generation, syntax error reporting,
ACK parsing, and EdiAckService database integration.
"""

import pytest
from unittest.mock import MagicMock, patch

from modules.integrations.models.edi import EdiStandard, EdiAckStatus
from modules.integrations.services.edi.edi_core import (
    parse_x12,
    parse_edifact,
    X12Builder,
    EdifactBuilder,
)
from modules.integrations.services.edi.edi_ack_service import (
    EdiSyntaxErrorInfo,
    TransactionAckDetail,
    FunctionalGroupAckDetail,
    ParsedAckReport,
    generate_997_ack,
    generate_contrl_ack,
    generate_edi_ack,
    parse_997_ack,
    parse_contrl_ack,
    parse_edi_ack,
    EdiAckService,
    edi_ack_service,
    X12_AK5_STATUS_CODES,
    X12_AK9_STATUS_CODES,
    EDIFACT_UCI_ACTION_CODES,
    EDIFACT_UCM_ACTION_CODES,
)


# ===========================================================================
# Sample EDI Documents for Testing
# ===========================================================================

SAMPLE_X12_850_INBOUND = (
    "ISA*00*          *00*          *ZZ*CARREFOUR_SND  *ZZ*NOVA_RCV       *260908*1430*U*00401*000000042*0*P*>~\n"
    "GS*PO*CARREFOUR_SND*NOVA_RCV*20260908*1430*101*X*004010~\n"
    "ST*850*0001~\n"
    "BEG*00*NE*PO-CRF-90210**20260908~\n"
    "PO1*1*100*CA*45.50*PE*CB*6291041000101~\n"
    "CTT*1*100~\n"
    "SE*6*0001~\n"
    "GE*1*101~\n"
    "IEA*1*000000042~"
)

SAMPLE_EDIFACT_ORDERS_INBOUND = (
    "UNB+UNOA:2+LULU_SND:ZZ+NOVA_RCV:ZZ+260908:1430+5001'\n"
    "UNH+MSG001+ORDERS:D:96A:UN:EAN008'\n"
    "BGM+220+PO-LULU-88401+9'\n"
    "LIN+1++6291041000101:SRV'\n"
    "QTY+21:200:KGM'\n"
    "UNT+5+MSG001'\n"
    "UNZ+1+5001'"
)


# ===========================================================================
# 1. ANSI X12 997 Functional Acknowledgment Tests
# ===========================================================================

def test_generate_997_ack_accepted_clean():
    """
    Test generating a standard 997 FA for a clean accepted 850 PO.
    """
    inbound = parse_x12(SAMPLE_X12_850_INBOUND)
    ack_x12 = generate_997_ack(
        inbound=inbound,
        ack_control_number="9970001",
    )

    # Validate envelope structure and swapped sender/receiver
    assert "ISA*00*" in ack_x12
    assert "NOVA_RCV" in ack_x12
    assert "CARREFOUR_SND" in ack_x12
    assert "GS*FA*NOVA_RCV*CARREFOUR_SND*" in ack_x12
    assert "ST*997*0001~" in ack_x12

    # AK1 referencing inbound GS (PO, 101)
    assert "AK1*PO*101*004010~" in ack_x12

    # AK2 referencing transaction set (850, 0001)
    assert "AK2*850*0001~" in ack_x12

    # AK5 acceptance
    assert "AK5*A~" in ack_x12

    # AK9 group acceptance (AK901=A, AK902=1, AK903=1, AK904=1)
    assert "AK9*A*1*1*1~" in ack_x12

    # Trailers
    assert "SE*" in ack_x12
    assert "GE*1*1~" in ack_x12
    assert "IEA*1*009970001~" in ack_x12


def test_generate_997_ack_with_rejection_and_syntax_errors():
    """
    Test generating a 997 FA reporting segment (AK3) and element (AK4) syntax errors.
    """
    inbound = parse_x12(SAMPLE_X12_850_INBOUND)

    # Inbound transaction 0001 has errors
    errors = [
        EdiSyntaxErrorInfo(
            segment_tag="PO1",
            segment_position=5,
            segment_error_code="8",  # Segment has data element errors
            element_position=4,
            element_error_code="7",  # Invalid code value
            bad_data_value="INVALID_PRICE",
            error_message="Invalid price value",
        ),
        EdiSyntaxErrorInfo(
            segment_tag="N1",
            segment_position=4,
            segment_error_code="3",  # Mandatory segment missing
            error_message="Missing ship-to N1 segment",
        ),
    ]

    ack_x12 = generate_997_ack(
        inbound=inbound,
        transaction_errors={"0001": errors},
        ack_control_number="9970002",
    )

    assert "ST*997*0001~" in ack_x12
    assert "AK1*PO*101*004010~" in ack_x12
    assert "AK2*850*0001~" in ack_x12

    # AK3 and AK4 segments
    assert "AK3*PO1*5**8~" in ack_x12
    assert "AK4*4**7*INVALID_PRICE~" in ack_x12
    assert "AK3*N1*4**3~" in ack_x12

    # AK5 Rejection
    assert "AK5*R*5~" in ack_x12

    # AK9 Group rejection (AK901=R, AK902=1, AK903=1, AK904=0)
    assert "AK9*R*1*1*0~" in ack_x12


def test_generate_997_ack_multi_transaction_partial_acceptance():
    """
    Test 997 FA with multiple transactions where one is accepted and one is rejected (AK9 = P).
    """
    builder = X12Builder(sender_id="SND_PARTNER", receiver_id="NOVA_DIST", control_number="12345")
    builder.start_group("PO", group_control_number="50")
    builder.start_transaction("850", control_number="TX01")
    builder.add_segment("BEG", "00", "SA", "PO-1")
    builder.end_transaction()
    builder.start_transaction("850", control_number="TX02")
    builder.add_segment("BEG", "00", "SA", "PO-2")
    builder.end_transaction()
    builder.end_group()

    inbound = builder.to_interchange()

    tx_errors = {
        "TX02": [
            EdiSyntaxErrorInfo(
                segment_tag="BEG",
                segment_position=2,
                segment_error_code="6",
            )
        ]
    }

    ack_x12 = generate_997_ack(
        inbound=inbound,
        transaction_errors=tx_errors,
        ack_control_number="55",
    )

    assert "AK2*850*TX01~" in ack_x12
    assert "AK5*A~" in ack_x12

    assert "AK2*850*TX02~" in ack_x12
    assert "AK5*R*5~" in ack_x12

    # AK9 Partial Acceptance: 2 included, 2 received, 1 accepted
    assert "AK9*P*2*2*1~" in ack_x12


def test_parse_997_ack():
    """
    Test parsing a 997 FA document into a structured ParsedAckReport.
    """
    sample_997 = (
        "ISA*00*          *00*          *ZZ*NOVA_RCV       *ZZ*CARREFOUR_SND  *260908*1500*U*00401*000000088*0*P*>~\n"
        "GS*FA*NOVA_RCV*CARREFOUR_SND*20260908*1500*1*X*004010~\n"
        "ST*997*0001~\n"
        "AK1*PO*101*004010~\n"
        "AK2*850*0001~\n"
        "AK3*PO1*5**8~\n"
        "AK4*4**7*BADPRICE~\n"
        "AK5*R*5~\n"
        "AK9*R*1*1*0~\n"
        "SE*8*0001~\n"
        "GE*1*1~\n"
        "IEA*1*000000088~"
    )

    report = parse_997_ack(sample_997)
    assert report.standard == "ANSI_X12"
    assert report.ack_type == "997"
    assert report.sender_id == "NOVA_RCV"
    assert report.receiver_id == "CARREFOUR_SND"
    assert report.ack_status == "REJECTED"
    assert report.acknowledged_control_number == "101"

    assert len(report.groups) == 1
    g = report.groups[0]
    assert g.functional_code == "PO"
    assert g.group_control_number == "101"
    assert g.status == "R"
    assert g.included_tx_count == 1
    assert g.accepted_tx_count == 0

    assert len(g.transactions) == 1
    tx = g.transactions[0]
    assert tx.doc_type == "850"
    assert tx.control_number == "0001"
    assert tx.status == "R"
    assert len(tx.syntax_errors) == 2
    assert tx.syntax_errors[0].segment_tag == "PO1"
    assert tx.syntax_errors[1].bad_data_value == "BADPRICE"


# ===========================================================================
# 2. UN/EDIFACT CONTRL Acknowledgment Tests
# ===========================================================================

def test_generate_contrl_ack_accepted_clean():
    """
    Test generating a standard UN/EDIFACT CONTRL message for an accepted ORDERS interchange.
    """
    inbound = parse_edifact(SAMPLE_EDIFACT_ORDERS_INBOUND)
    ack_edifact = generate_contrl_ack(
        inbound=inbound,
        ack_control_number="6001",
    )

    # UNB Envelope with swapped sender and receiver
    assert "UNB+UNOA:2+NOVA_RCV:ZZ+LULU_SND:ZZ+" in ack_edifact
    assert "+6001'" in ack_edifact

    # UNH Message header
    assert "UNH+1+CONTRL:D:96A:UN:EAN008'" in ack_edifact

    # UCI Interchange response (5001, LULU_SND:ZZ, NOVA_RCV:ZZ, 7=Accepted)
    assert "UCI+5001+LULU_SND:ZZ+NOVA_RCV:ZZ+7'" in ack_edifact

    # UCM Message response (MSG001, ORDERS:D:96A:UN:EAN008, 7=Accepted)
    assert "UCM+MSG001+ORDERS:D:96A:UN:EAN008+7'" in ack_edifact

    # UNT and UNZ trailers
    assert "UNT*4*1'" in ack_edifact or "UNT+4+1'" in ack_edifact
    assert "UNZ+1+6001'" in ack_edifact


def test_generate_contrl_ack_with_syntax_errors():
    """
    Test generating a CONTRL message reporting message rejection and segment/element errors (UCS/UCD).
    """
    inbound = parse_edifact(SAMPLE_EDIFACT_ORDERS_INBOUND)

    errors = [
        EdiSyntaxErrorInfo(
            segment_position=4,
            segment_error_code="12",  # Invalid segment tag
            element_position=2,
            component_position=1,
            element_error_code="12",  # Invalid data element value
            error_message="Invalid quantity component",
        )
    ]

    ack_edifact = generate_contrl_ack(
        inbound=inbound,
        message_errors={"MSG001": errors},
        ack_control_number="6002",
    )

    # UCI rejected (4)
    assert "UCI+5001+LULU_SND:ZZ+NOVA_RCV:ZZ+4'" in ack_edifact

    # UCM rejected (4)
    assert "UCM+MSG001+ORDERS:D:96A:UN:EAN008+4'" in ack_edifact

    # UCS segment error
    assert "UCS+4+12'" in ack_edifact

    # UCD element error (pos 2:1)
    assert "UCD+12+2:1'" in ack_edifact


def test_parse_contrl_ack():
    """
    Test parsing an inbound CONTRL document into a structured ParsedAckReport.
    """
    sample_contrl = (
        "UNB+UNOA:2+NOVA_RCV:ZZ+LULU_SND:ZZ+260908:1500+7701'\n"
        "UNH+1+CONTRL:D:96A:UN:EAN008'\n"
        "UCI+5001+LULU_SND:ZZ+NOVA_RCV:ZZ+8'\n"
        "UCM+MSG001+ORDERS:D:96A:UN:EAN008+8+12'\n"
        "UCS+4+12'\n"
        "UCD+14+2:1'\n"
        "UNT+6+1'\n"
        "UNZ+1+7701'"
    )

    report = parse_contrl_ack(sample_contrl)
    assert report.standard == "EDIFACT"
    assert report.ack_type == "CONTRL"
    assert report.sender_id == "NOVA_RCV"
    assert report.receiver_id == "LULU_SND"
    assert report.ack_status == "ACCEPTED_WITH_ERRORS"
    assert report.acknowledged_control_number == "5001"

    assert len(report.messages) == 1
    m = report.messages[0]
    assert m.doc_type == "ORDERS"
    assert m.control_number == "MSG001"
    assert m.status == "8"
    assert len(m.syntax_errors) == 2
    assert m.syntax_errors[0].segment_position == 4
    assert m.syntax_errors[1].element_position == 2
    assert m.syntax_errors[1].component_position == 1


# ===========================================================================
# 3. Universal Generator & Parser Tests
# ===========================================================================

def test_generate_edi_ack_universal():
    # Test X12 auto-dispatch
    x12_payload, x12_status, x12_summary = generate_edi_ack(
        inbound=SAMPLE_X12_850_INBOUND,
        is_accepted=True,
    )
    assert x12_status == EdiAckStatus.ACCEPTED
    assert x12_summary["document_type"] == "997"
    assert "ISA*00*" in x12_payload

    # Test EDIFACT auto-dispatch
    edifact_payload, edifact_status, edifact_summary = generate_edi_ack(
        inbound=SAMPLE_EDIFACT_ORDERS_INBOUND,
        is_accepted=False,
    )
    assert edifact_status == EdiAckStatus.REJECTED
    assert edifact_summary["document_type"] == "CONTRL"
    assert "UNB+UNOA:2+" in edifact_payload


def test_parse_edi_ack_universal():
    # X12 997
    sample_997 = generate_997_ack(SAMPLE_X12_850_INBOUND, default_status="A")
    parsed_997 = parse_edi_ack(sample_997)
    assert parsed_997.standard == "ANSI_X12"
    assert parsed_997.ack_status == "ACCEPTED"

    # EDIFACT CONTRL
    sample_contrl = generate_contrl_ack(SAMPLE_EDIFACT_ORDERS_INBOUND, default_action_code="7")
    parsed_contrl = parse_edi_ack(sample_contrl)
    assert parsed_contrl.standard == "EDIFACT"
    assert parsed_contrl.ack_status == "ACCEPTED"


# ===========================================================================
# 4. EdiAckService Database & Workflow Integration Tests
# ===========================================================================

def test_edi_ack_service_create_and_record_ack_mocked():
    mock_repo = MagicMock()
    mock_partner_repo = MagicMock()

    mock_repo.get.return_value = {
        "id": 101,
        "standard": "ANSI_X12",
        "document_type": "850",
        "direction": "INBOUND",
        "partner_id": 5,
        "raw_payload": SAMPLE_X12_850_INBOUND,
    }
    mock_partner_repo.get.return_value = {
        "id": 5,
        "partner_code": "CRF-UAE",
        "edi_standard": "ANSI_X12",
    }
    mock_repo.update.return_value = {"id": 101, "ack_status": "ACCEPTED"}
    mock_repo.create.return_value = {"id": 102, "document_type": "997"}

    service = EdiAckService(repo=mock_repo, partner_repo=mock_partner_repo)

    with patch.object(service, "get_next_ack_control_number", return_value="9990001"):
        result = service.create_and_record_ack(transaction_id=101, is_accepted=True)

        assert result["inbound_transaction_id"] == 101
        assert result["ack_status"] == "ACCEPTED"
        assert result["ack_document_type"] == "997"
        assert result["ack_control_number"] == "9990001"
        assert "ST*997*0001~" in result["ack_payload"]

        # Inbound updated with ACK payload
        mock_repo.update.assert_called_once()
        # Outbound ACK transaction created
        mock_repo.create.assert_called_once()


def test_edi_ack_service_process_inbound_ack_mocked():
    mock_repo = MagicMock()
    mock_repo.list.return_value = [
        {
            "id": 201,
            "direction": "OUTBOUND",
            "control_number": "101",
            "status": "PROCESSED",
        }
    ]
    mock_repo.update.return_value = {"id": 201, "status": "ACKNOWLEDGED"}

    sample_997 = (
        "ISA*00*          *00*          *ZZ*CARREFOUR      *ZZ*NOVA_DIST      *260908*1500*U*00401*000000099*0*P*>~\n"
        "GS*FA*CARREFOUR*NOVA_DIST*20260908*1500*1*X*004010~\n"
        "ST*997*0001~\n"
        "AK1*PO*101*004010~\n"
        "AK2*850*0001~\n"
        "AK5*A~\n"
        "AK9*A*1*1*1~\n"
        "SE*6*0001~\n"
        "GE*1*1~\n"
        "IEA*1*000000099~"
    )

    service = EdiAckService(repo=mock_repo)
    res = service.process_inbound_ack(sample_997, partner_id=5)

    assert res["status"] == "PROCESSED"
    assert res["matched_transaction_id"] == 201
    assert res["ack_report"]["ack_status"] == "ACCEPTED"

    mock_repo.update.assert_called_once_with(
        201,
        {
            "ack_status": "ACCEPTED",
            "ack_payload": sample_997,
            "status": "ACKNOWLEDGED",
        },
    )
