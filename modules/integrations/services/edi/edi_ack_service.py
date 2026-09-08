"""
Nova ERP — Functional Acknowledgment Generation & Interpretation Service
Provides ANSI X12 997 Functional Acknowledgment and UN/EDIFACT CONTRL acknowledgment
generation, syntax error reporting (AK3/AK4, UCS/UCD), ACK parsing, and database persistence.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

from packages.database.connection import get_connection, release_connection, db_transaction
from modules.core.context import get_current_tenant
from modules.core.services.base import CrudService
from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiAckStatus,
    EdiDirection,
    EDI_TRANSACTION_REPO,
    EDI_PARTNER_REPO,
)
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    EdiSegment,
    EdiTransactionSet,
    EdiFunctionalGroup,
    EdiInterchange,
    detect_edi_standard,
    parse_edi,
    parse_x12,
    parse_edifact,
    serialize_x12,
    serialize_edifact,
    serialize_edi,
    EdiSyntaxError,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# 1. Standard Error Code Tables & Dictionaries
# ===========================================================================

# ANSI X12 AK501: Transaction Set Acknowledgment Code
X12_AK5_STATUS_CODES: Dict[str, str] = {
    "A": "Accepted",
    "E": "Accepted But Errors Were Noted",
    "M": "Rejected, Message Authentication Code (MAC) Failed",
    "R": "Rejected",
    "W": "Rejected, Assurance Failed Validity Tests",
    "X": "Rejected, Content After Decryption Could Not Be Analyzed",
}

# ANSI X12 AK901: Functional Group Acknowledge Code
X12_AK9_STATUS_CODES: Dict[str, str] = {
    "A": "Accepted",
    "E": "Accepted, But Errors Were Noted",
    "M": "Rejected, Message Authentication Code (MAC) Failed",
    "P": "Partially Accepted, At Least One Transaction Set Was Rejected",
    "R": "Rejected",
    "W": "Rejected, Assurance Failed Validity Tests",
    "X": "Rejected, Content After Decryption Could Not Be Analyzed",
}

# ANSI X12 AK502-AK506: Transaction Set Syntax Error Codes
X12_AK5_ERROR_CODES: Dict[str, str] = {
    "1": "Transaction Set Not Supported",
    "2": "Transaction Set Trailer Missing",
    "3": "Transaction Set Control Number in Header and Trailer Do Not Agree",
    "4": "Number of Included Segments Does Not Match Actual Count",
    "5": "One or More Segments in Error",
    "6": "Missing or Invalid Transaction Set Identifier",
    "7": "Missing or Invalid Transaction Set Control Number",
}

# ANSI X12 AK905-AK909: Functional Group Syntax Error Codes
X12_AK9_ERROR_CODES: Dict[str, str] = {
    "1": "Functional Group Not Supported",
    "2": "Functional Group Version Not Supported",
    "3": "Functional Group Trailer Missing",
    "4": "Group Control Number in Header and Trailer Do Not Agree",
    "5": "Number of Included Transaction Sets Does Not Match Actual Count",
    "6": "Group Control Number Violates Syntax",
}

# ANSI X12 AK304: Segment Syntax Error Codes
X12_AK3_ERROR_CODES: Dict[str, str] = {
    "1": "Unrecognized segment ID",
    "2": "Unexpected segment",
    "3": "Mandatory segment missing",
    "4": "Loop occurs over maximum times",
    "5": "Segment exceeds maximum use",
    "6": "Segment not in defined transaction set",
    "7": "Segment not in proper sequence",
    "8": "Segment has data element errors",
}

# ANSI X12 AK403: Data Element Syntax Error Codes
X12_AK4_ERROR_CODES: Dict[str, str] = {
    "1": "Mandatory data element missing",
    "2": "Conditional required data element missing",
    "3": "Too many data elements",
    "4": "Data element too short",
    "5": "Data element too long",
    "6": "Invalid character in data element",
    "7": "Invalid code value",
    "8": "Invalid date",
    "9": "Invalid time",
    "10": "Exclusion condition violated",
}

# UN/EDIFACT UCI04: Interchange Action Codes
EDIFACT_UCI_ACTION_CODES: Dict[str, str] = {
    "7": "Accepted / Acknowledged",
    "4": "Rejected",
    "8": "Acknowledged with errors",
}

# UN/EDIFACT UCM03: Message Action Codes
EDIFACT_UCM_ACTION_CODES: Dict[str, str] = {
    "7": "Accepted",
    "4": "Rejected",
    "8": "Acknowledged with errors",
}

# UN/EDIFACT UCI05: Interchange Syntax Error Codes
EDIFACT_UCI_SYNTAX_ERROR_CODES: Dict[str, str] = {
    "2": "Syntax version or level not supported",
    "7": "Recipient is not actual recipient",
    "12": "Invalid value",
    "13": "Missing mandatory service segment",
    "15": "Not supported in this position",
    "18": "Unspecified syntax error",
}

# UN/EDIFACT UCM04: Message Syntax Error Codes
EDIFACT_UCM_SYNTAX_ERROR_CODES: Dict[str, str] = {
    "12": "Invalid value",
    "13": "Missing mandatory segment",
    "14": "Value not supported in this position",
    "15": "Not supported in this position",
    "16": "Too many constituents",
    "17": "No agreement",
    "18": "Unspecified error",
}

# UN/EDIFACT UCS02: Segment Syntax Error Codes
EDIFACT_UCS_ERROR_CODES: Dict[str, str] = {
    "12": "Invalid segment tag",
    "13": "Missing mandatory segment",
    "14": "Value not supported in this position",
    "15": "Segment not supported in this position",
    "16": "Too many segment repetitions",
    "17": "Segment out of sequence",
}

# UN/EDIFACT UCD01: Data Element Syntax Error Codes
EDIFACT_UCD_ERROR_CODES: Dict[str, str] = {
    "12": "Invalid data element value",
    "13": "Missing mandatory data element",
    "14": "Value not supported in this position",
    "15": "Data element not supported in this position",
    "16": "Too many constituent elements",
    "17": "Code value not recognized",
}


# ===========================================================================
# 2. Domain Models for Error Details & ACK Reports
# ===========================================================================

class EdiSyntaxErrorInfo(BaseModel):
    """
    Detailed syntax or data validation error on a segment or data element.
    """
    segment_tag: Optional[str] = None
    segment_position: Optional[int] = None
    loop_id: Optional[str] = None
    segment_error_code: Optional[str] = None
    element_position: Optional[int] = None
    component_position: Optional[int] = None
    element_error_code: Optional[str] = None
    bad_data_value: Optional[str] = None
    error_message: Optional[str] = None


class TransactionAckDetail(BaseModel):
    """
    Acknowledgment report for a single business document transaction set / message.
    """
    doc_type: str
    control_number: str
    status: str = "A"  # X12: A, E, R; EDIFACT: 7, 8, 4
    syntax_errors: List[EdiSyntaxErrorInfo] = Field(default_factory=list)
    error_codes: List[str] = Field(default_factory=list)
    status_description: Optional[str] = None


class FunctionalGroupAckDetail(BaseModel):
    """
    Acknowledgment report for an X12 functional group (GS/GE).
    """
    functional_code: str
    group_control_number: str
    version: str = "004010"
    status: str = "A"  # A, E, P, R
    included_tx_count: int = 1
    received_tx_count: int = 1
    accepted_tx_count: int = 1
    transactions: List[TransactionAckDetail] = Field(default_factory=list)
    syntax_error_codes: List[str] = Field(default_factory=list)
    status_description: Optional[str] = None


class ParsedAckReport(BaseModel):
    """
    Unified parsed result from an inbound 997 FA or CONTRL document.
    """
    standard: str
    ack_type: str  # "997" or "CONTRL"
    sender_id: str
    receiver_id: str
    control_number: str
    ack_status: str  # "ACCEPTED", "REJECTED", "ACCEPTED_WITH_ERRORS", "PARTIALLY_ACCEPTED"
    acknowledged_control_number: Optional[str] = None
    groups: List[FunctionalGroupAckDetail] = Field(default_factory=list)
    messages: List[TransactionAckDetail] = Field(default_factory=list)
    raw_payload: str = ""


# ===========================================================================
# 3. ANSI X12 997 Functional Acknowledgment Generator
# ===========================================================================

def generate_997_ack(
    inbound: Union[str, EdiInterchange],
    partner: Optional[Any] = None,
    sender_id: Optional[str] = None,
    receiver_id: Optional[str] = None,
    sender_qualifier: Optional[str] = None,
    receiver_qualifier: Optional[str] = None,
    ack_control_number: Optional[str] = None,
    transaction_errors: Optional[Dict[str, List[EdiSyntaxErrorInfo]]] = None,
    default_status: str = "A",
    delimiters: Optional[EdiDelimiters] = None,
    is_test: Optional[bool] = None,
    line_breaks: bool = True,
) -> str:
    """
    Generates an ANSI X12 997 Functional Acknowledgment interchange message in response to an inbound X12 document.
    
    Structure:
      ISA -> GS (FA) -> ST (997) -> AK1 -> [AK2 -> (AK3/AK4) -> AK5]* -> AK9 -> SE -> GE -> IEA
      
    Args:
        inbound: Inbound X12 EdiInterchange object or raw string.
        partner: Optional EdiPartner model/dict for delimiter and partner defaults.
        sender_id: Outbound sender ID (defaults to inbound receiver_id).
        receiver_id: Outbound receiver ID (defaults to inbound sender_id).
        sender_qualifier: Outbound sender qualifier (defaults to inbound receiver_qualifier).
        receiver_qualifier: Outbound receiver qualifier (defaults to inbound sender_qualifier).
        ack_control_number: Control number for the 997 interchange (auto-generated if None).
        transaction_errors: Dict mapping transaction control number -> list of EdiSyntaxErrorInfo.
        default_status: Default transaction status ('A'=Accepted, 'R'=Rejected, 'E'=Accepted with Errors).
        delimiters: Delimiter overrides.
        is_test: Whether usage indicator is test (T) or production (P).
        line_breaks: Whether to format output with newlines.
        
    Returns:
        Formatted ANSI X12 997 Functional Acknowledgment string.
    """
    if isinstance(inbound, str):
        interchange = parse_x12(inbound, delimiters)
    else:
        interchange = inbound

    active_delims = delimiters or (EdiDelimiters.from_partner(partner) if partner else interchange.delimiters) or EdiDelimiters.x12_default()
    tx_err_map = transaction_errors or {}

    # Swap sender and receiver for outbound response
    out_sender = sender_id or interchange.receiver_id or "NOVA_ERP"
    out_receiver = receiver_id or interchange.sender_id or "PARTNER"
    out_sender_qual = sender_qualifier or interchange.receiver_qualifier or "ZZ"
    out_receiver_qual = receiver_qualifier or interchange.sender_qualifier or "ZZ"
    test_mode = is_test if is_test is not None else interchange.is_test

    now = datetime.now(timezone.utc)
    date_yymmdd = now.strftime("%y%m%d")
    date_yyyymmdd = now.strftime("%Y%m%d")
    time_hhmm = now.strftime("%H%M")
    ctrl_num = str(ack_control_number or interchange.control_number or "1")
    ctrl_num_9 = ctrl_num.zfill(9)[-9:]

    lines: List[str] = []
    term = active_delims.segment_terminator
    sep = active_delims.element_separator
    subsep = active_delims.subelement_separator
    eol = "\n" if line_breaks else ""

    # 1. ISA Envelope
    isa_elements = [
        "00",                                   # ISA01
        f"{'':10}",                             # ISA02
        "00",                                   # ISA03
        f"{'':10}",                             # ISA04
        out_sender_qual.ljust(2)[:2],           # ISA05
        out_sender.ljust(15)[:15],              # ISA06
        out_receiver_qual.ljust(2)[:2],         # ISA07
        out_receiver.ljust(15)[:15],            # ISA08
        date_yymmdd,                            # ISA09
        time_hhmm,                              # ISA10
        "U",                                    # ISA11
        "00401",                                # ISA12
        ctrl_num_9,                             # ISA13
        "0",                                    # ISA14
        "T" if test_mode else "P",              # ISA15
        subsep,                                 # ISA16
    ]
    lines.append(f"ISA{sep}{sep.join(isa_elements)}{term}")

    # 2. GS Functional Group Header (Functional Code: FA)
    group_ctrl = "1"
    gs_elements = [
        "FA",                                   # GS01: Functional Identifier Code (FA = Functional Acknowledgment)
        out_sender,                             # GS02
        out_receiver,                           # GS03
        date_yyyymmdd,                          # GS04
        time_hhmm,                              # GS05
        group_ctrl,                             # GS06
        "X",                                    # GS07: Responsible Agency Code
        "004010",                               # GS08: Version / Release
    ]
    lines.append(f"GS{sep}{sep.join(gs_elements)}{term}")

    # 3. ST Transaction Set Header
    tx_ctrl = "0001"
    lines.append(f"ST{sep}997{sep}{tx_ctrl}{term}")
    st_se_segment_count = 1  # count ST

    # Process functional groups from inbound interchange
    inbound_groups = interchange.groups
    if not inbound_groups and interchange.messages:
        # Synthesize functional group from standalone messages
        default_fg = "PO"
        if interchange.messages and interchange.messages[0].doc_type == "856":
            default_fg = "SH"
        elif interchange.messages and interchange.messages[0].doc_type == "810":
            default_fg = "IN"
        elif interchange.messages and interchange.messages[0].doc_type == "832":
            default_fg = "SC"

        inbound_groups = [
            EdiFunctionalGroup(
                functional_code=default_fg,
                group_control_number=interchange.control_number or "1",
                version="004010",
                transactions=interchange.messages,
            )
        ]

    for g_idx, group in enumerate(inbound_groups, start=1):
        fg_code = group.functional_code or "PO"
        fg_ctrl = group.group_control_number or str(g_idx)
        fg_ver = group.version or "004010"

        # AK1: Functional Group Response Header
        lines.append(f"AK1{sep}{fg_code}{sep}{fg_ctrl}{sep}{fg_ver}{term}")
        st_se_segment_count += 1

        tx_list = group.transactions
        total_tx = len(tx_list)
        accepted_tx = 0
        rejected_tx = 0
        errors_noted_tx = 0

        for tx_idx, tx in enumerate(tx_list, start=1):
            t_code = tx.doc_type or "850"
            t_ctrl = tx.control_number or str(tx_idx).zfill(4)

            # AK2: Transaction Set Response Header
            lines.append(f"AK2{sep}{t_code}{sep}{t_ctrl}{term}")
            st_se_segment_count += 1

            errors = tx_err_map.get(t_ctrl) or tx_err_map.get(str(tx_idx)) or []
            tx_status = default_status

            if errors:
                # Check whether errors cause rejection or errors noted
                has_rejection = any(
                    (e.segment_error_code in ("1", "2", "3", "6", "7") or e.element_error_code in ("1", "2", "6", "7"))
                    for e in errors
                )
                tx_status = "R" if has_rejection else "E"

                for err in errors:
                    # AK3: Data Segment Note
                    if err.segment_tag:
                        ak3_pos = str(err.segment_position or 1)
                        ak3_loop = err.loop_id or ""
                        ak3_err = str(err.segment_error_code or "8")
                        lines.append(f"AK3{sep}{err.segment_tag}{sep}{ak3_pos}{sep}{ak3_loop}{sep}{ak3_err}{term}")
                        st_se_segment_count += 1

                    # AK4: Data Element Note
                    if err.element_position is not None:
                        ak4_pos = str(err.element_position)
                        if err.component_position:
                            ak4_pos = f"{err.element_position}{subsep}{err.component_position}"
                        ak4_ref = ""
                        ak4_err = str(err.element_error_code or "7")
                        ak4_val = (err.bad_data_value or "")[:99]
                        lines.append(f"AK4{sep}{ak4_pos}{sep}{ak4_ref}{sep}{ak4_err}{sep}{ak4_val}{term}")
                        st_se_segment_count += 1

            if tx_status == "A":
                accepted_tx += 1
                lines.append(f"AK5{sep}A{term}")
            elif tx_status == "E":
                accepted_tx += 1
                errors_noted_tx += 1
                lines.append(f"AK5{sep}E{sep}5{term}")
            else:
                rejected_tx += 1
                lines.append(f"AK5{sep}R{sep}5{term}")

            st_se_segment_count += 1

        # Determine overall AK9 Functional Group status
        if rejected_tx == 0 and errors_noted_tx == 0:
            ak9_status = "A"  # Accepted
        elif rejected_tx == 0 and errors_noted_tx > 0:
            ak9_status = "E"  # Accepted with errors
        elif accepted_tx > 0 and rejected_tx > 0:
            ak9_status = "P"  # Partially accepted
        else:
            ak9_status = "R"  # Rejected

        # AK9: Functional Group Response Trailer
        # AK901: Status, AK902: Included, AK903: Received, AK904: Accepted
        lines.append(f"AK9{sep}{ak9_status}{sep}{total_tx}{sep}{total_tx}{sep}{accepted_tx}{term}")
        st_se_segment_count += 1

    # 4. SE Transaction Set Trailer
    st_se_segment_count += 1  # count SE itself
    lines.append(f"SE{sep}{st_se_segment_count}{sep}{tx_ctrl}{term}")

    # 5. GE Functional Group Trailer
    lines.append(f"GE{sep}1{sep}{group_ctrl}{term}")

    # 6. IEA Interchange Trailer
    lines.append(f"IEA{sep}1{sep}{ctrl_num_9}{term}")

    return eol.join(lines) + (eol if line_breaks else "")


# ===========================================================================
# 4. UN/EDIFACT CONTRL Acknowledgment Generator
# ===========================================================================

def generate_contrl_ack(
    inbound: Union[str, EdiInterchange],
    partner: Optional[Any] = None,
    sender_id: Optional[str] = None,
    receiver_id: Optional[str] = None,
    sender_qualifier: Optional[str] = None,
    receiver_qualifier: Optional[str] = None,
    ack_control_number: Optional[str] = None,
    message_errors: Optional[Dict[str, List[EdiSyntaxErrorInfo]]] = None,
    default_action_code: str = "7",  # 7=Accepted, 4=Rejected, 8=Accepted with errors
    delimiters: Optional[EdiDelimiters] = None,
    is_test: Optional[bool] = None,
    line_breaks: bool = True,
) -> str:
    """
    Generates a UN/EDIFACT CONTRL (Syntax and Service Report / Functional Acknowledgment)
    interchange message in response to an inbound EDIFACT document.
    
    Structure:
      UNB -> UNH (CONTRL) -> UCI -> [UCM -> (UCS/UCD)*]* -> UNT -> UNZ
      
    Args:
        inbound: Inbound EDIFACT EdiInterchange object or raw string.
        partner: Optional EdiPartner model/dict.
        sender_id: Outbound sender ID (defaults to inbound receiver_id).
        receiver_id: Outbound receiver ID (defaults to inbound sender_id).
        sender_qualifier: Outbound sender qualifier (defaults to inbound receiver_qualifier).
        receiver_qualifier: Outbound receiver qualifier (defaults to inbound sender_qualifier).
        ack_control_number: Control number for the CONTRL interchange.
        message_errors: Dict mapping message reference number -> list of EdiSyntaxErrorInfo.
        default_action_code: Default action code ('7'=Accepted, '4'=Rejected, '8'=Errors noted).
        delimiters: Delimiter overrides.
        is_test: Whether test flag should be set in UNB.
        line_breaks: Whether to format output with newlines.
        
    Returns:
        Formatted UN/EDIFACT CONTRL string.
    """
    if isinstance(inbound, str):
        interchange = parse_edifact(inbound, delimiters)
    else:
        interchange = inbound

    active_delims = delimiters or (EdiDelimiters.from_partner(partner) if partner else interchange.delimiters) or EdiDelimiters.edifact_default()
    msg_err_map = message_errors or {}

    out_sender = sender_id or interchange.receiver_id or "NOVA_ERP"
    out_receiver = receiver_id or interchange.sender_id or "PARTNER"
    out_sender_qual = sender_qualifier or interchange.receiver_qualifier or "ZZ"
    out_receiver_qual = receiver_qualifier or interchange.sender_qualifier or "ZZ"
    test_mode = is_test if is_test is not None else interchange.is_test

    now = datetime.now(timezone.utc)
    date_yymmdd = now.strftime("%y%m%d")
    time_hhmm = now.strftime("%H%M")
    ctrl_num = str(ack_control_number or interchange.control_number or "1")

    lines: List[str] = []
    term = active_delims.segment_terminator
    sep = active_delims.element_separator
    subsep = active_delims.subelement_separator
    eol = "\n" if line_breaks else ""

    # 1. UNB Interchange Header
    unb_elements = [
        f"UNOA{subsep}2",
        f"{out_sender}{subsep}{out_sender_qual}",
        f"{out_receiver}{subsep}{out_receiver_qual}",
        f"{date_yymmdd}{subsep}{time_hhmm}",
        ctrl_num,
    ]
    if test_mode:
        while len(unb_elements) < 10:
            unb_elements.append("")
        unb_elements.append("1")

    lines.append(f"UNB{sep}{sep.join(unb_elements)}{term}")

    # 2. UNH Message Header (CONTRL:D:96A:UN:EAN008 or CONTRL:2:D:F)
    msg_ref = "1"
    msg_type = f"CONTRL{subsep}D{subsep}96A{subsep}UN{subsep}EAN008"
    lines.append(f"UNH{sep}{msg_ref}{sep}{msg_type}{term}")
    unh_unt_segment_count = 1  # count UNH

    # 3. UCI Interchange Response Segment
    # UCI+<inbound_ctrl_ref>+<inbound_sender>+<inbound_receiver>+<action_code>+<error_code>+<service_segment>'
    inbound_ctrl = interchange.control_number or "1"
    inbound_sender_comp = f"{interchange.sender_id}{subsep}{interchange.sender_qualifier or 'ZZ'}"
    inbound_rcvr_comp = f"{interchange.receiver_id}{subsep}{interchange.receiver_qualifier or 'ZZ'}"

    # Determine overall interchange action code
    total_msgs = interchange.all_transactions()
    has_any_rejection = False
    has_any_errors = False

    for idx, msg in enumerate(total_msgs, start=1):
        m_ref = msg.control_number or str(idx)
        errs = msg_err_map.get(m_ref) or msg_err_map.get(str(idx)) or []
        if errs:
            has_any_errors = True
            if any(e.segment_error_code in ("12", "13", "17") or e.element_error_code in ("12", "13", "17") for e in errs):
                has_any_rejection = True

    if default_action_code == "4" or has_any_rejection:
        uci_action = "4"  # Rejected
    elif default_action_code == "8" or has_any_errors:
        uci_action = "8"  # Acknowledged with errors
    else:
        uci_action = "7"  # Accepted

    uci_elements = [
        inbound_ctrl,
        inbound_sender_comp,
        inbound_rcvr_comp,
        uci_action,
    ]
    lines.append(f"UCI{sep}{sep.join(uci_elements)}{term}")
    unh_unt_segment_count += 1

    # 4. UCM Message Response Loop
    for idx, msg in enumerate(total_msgs, start=1):
        m_ref = msg.control_number or str(idx)
        m_type = msg.doc_type or "ORDERS"
        m_version = f"{m_type}{subsep}D{subsep}96A{subsep}UN{subsep}EAN008"

        errs = msg_err_map.get(m_ref) or msg_err_map.get(str(idx)) or []
        m_action = default_action_code

        if errs:
            if any(e.segment_error_code in ("12", "13", "17") or e.element_error_code in ("12", "13", "17") for e in errs):
                m_action = "4"  # Rejected
            else:
                m_action = "8"  # Acknowledged with errors
        elif default_action_code not in ("4", "8"):
            m_action = "7"  # Accepted

        ucm_elements = [
            m_ref,
            m_version,
            m_action,
        ]
        lines.append(f"UCM{sep}{sep.join(ucm_elements)}{term}")
        unh_unt_segment_count += 1

        # Optional UCS (Segment Error) & UCD (Data Element Error)
        for err in errs:
            if err.segment_position is not None:
                ucs_code = str(err.segment_error_code or "12")
                lines.append(f"UCS{sep}{err.segment_position}{sep}{ucs_code}{term}")
                unh_unt_segment_count += 1

            if err.element_position is not None:
                ucd_code = str(err.element_error_code or "12")
                pos_str = str(err.element_position)
                if err.component_position:
                    pos_str = f"{err.element_position}{subsep}{err.component_position}"
                lines.append(f"UCD{sep}{ucd_code}{sep}{pos_str}{term}")
                unh_unt_segment_count += 1

    # 5. UNT Message Trailer
    unh_unt_segment_count += 1  # count UNT itself
    lines.append(f"UNT{sep}{unh_unt_segment_count}{sep}{msg_ref}{term}")

    # 6. UNZ Interchange Trailer (1 message in CONTRL interchange)
    lines.append(f"UNZ{sep}1{sep}{ctrl_num}{term}")

    return eol.join(lines) + (eol if line_breaks else "")


# ===========================================================================
# 5. Universal Functional Acknowledgment Generator
# ===========================================================================

def generate_edi_ack(
    inbound: Union[str, EdiInterchange],
    partner: Optional[Any] = None,
    standard: Optional[Union[str, EdiStandard]] = None,
    is_accepted: bool = True,
    errors: Optional[Union[List[EdiSyntaxErrorInfo], Dict[str, List[EdiSyntaxErrorInfo]]]] = None,
    ack_control_number: Optional[str] = None,
    delimiters: Optional[EdiDelimiters] = None,
    line_breaks: bool = True,
) -> Tuple[str, EdiAckStatus, Dict[str, Any]]:
    """
    Universal entry point to generate a Functional Acknowledgment (997 FA or CONTRL)
    for any incoming EDI document.
    
    Args:
        inbound: Inbound EDI payload string or parsed EdiInterchange.
        partner: Trading partner model or dict.
        standard: Standard override (ANSI_X12 or EDIFACT).
        is_accepted: True for acceptance, False for rejection.
        errors: Error details (list or dict mapping tx/msg ctrl -> errors).
        ack_control_number: Outbound ACK control number.
        delimiters: Delimiter overrides.
        line_breaks: Newline formatting toggle.
        
    Returns:
        Tuple of (ack_payload_str, EdiAckStatus_enum, summary_dict).
    """
    if isinstance(inbound, str):
        detected_std = detect_edi_standard(inbound) if not standard else standard
        if isinstance(detected_std, str) and detected_std.upper() == "EDIFACT":
            interchange = parse_edifact(inbound, delimiters)
        else:
            interchange = parse_x12(inbound, delimiters)
    else:
        interchange = inbound

    std = interchange.standard
    if isinstance(std, EdiStandard):
        std_str = std.value
    else:
        std_str = str(std).upper()

    # Format errors mapping
    err_map: Dict[str, List[EdiSyntaxErrorInfo]] = {}
    if isinstance(errors, list):
        # Apply to all transactions/messages
        for tx in interchange.all_transactions():
            err_map[tx.control_number] = errors
    elif isinstance(errors, dict):
        err_map = errors

    if std_str == "EDIFACT" or std_str == EdiStandard.EDIFACT.value:
        action_code = "7" if is_accepted and not err_map else ("8" if is_accepted and err_map else "4")
        payload = generate_contrl_ack(
            inbound=interchange,
            partner=partner,
            ack_control_number=ack_control_number,
            message_errors=err_map,
            default_action_code=action_code,
            delimiters=delimiters,
            line_breaks=line_breaks,
        )
        status_enum = EdiAckStatus.ACCEPTED if action_code == "7" else (
            EdiAckStatus.ACCEPTED_WITH_ERRORS if action_code == "8" else EdiAckStatus.REJECTED
        )
        doc_type = "CONTRL"
    else:
        status_code = "A" if is_accepted and not err_map else ("E" if is_accepted and err_map else "R")
        payload = generate_997_ack(
            inbound=interchange,
            partner=partner,
            ack_control_number=ack_control_number,
            transaction_errors=err_map,
            default_status=status_code,
            delimiters=delimiters,
            line_breaks=line_breaks,
        )
        status_enum = EdiAckStatus.ACCEPTED if status_code == "A" else (
            EdiAckStatus.ACCEPTED_WITH_ERRORS if status_code == "E" else EdiAckStatus.REJECTED
        )
        doc_type = "997"

    summary = {
        "standard": std_str,
        "document_type": doc_type,
        "ack_status": status_enum.value,
        "inbound_control_number": interchange.control_number,
        "inbound_sender": interchange.sender_id,
        "inbound_receiver": interchange.receiver_id,
        "transactions_count": len(interchange.all_transactions()),
        "errors_count": sum(len(v) for v in err_map.values()),
    }

    return payload, status_enum, summary


# ===========================================================================
# 6. Functional Acknowledgment Interpreters / Parsers
# ===========================================================================

def parse_997_ack(raw_997: Union[str, EdiInterchange]) -> ParsedAckReport:
    """
    Parses an inbound ANSI X12 997 Functional Acknowledgment into a structured ParsedAckReport.
    Extracts AK1, AK2, AK3, AK4, AK5, and AK9 segment details.
    """
    if isinstance(raw_997, str):
        interchange = parse_x12(raw_997)
        raw_str = raw_997
    else:
        interchange = raw_997
        raw_str = serialize_x12(interchange)

    all_txs = interchange.all_transactions()
    groups_report: List[FunctionalGroupAckDetail] = []
    overall_status = "ACCEPTED"

    for tx in all_txs:
        if tx.doc_type != "997" and not tx.find_first("AK1"):
            continue

        current_fg: Optional[FunctionalGroupAckDetail] = None
        current_tx_ack: Optional[TransactionAckDetail] = None

        for seg in tx.segments:
            tag = seg.tag

            if tag == "AK1":
                # AK1*<fg_code>*<group_ctrl>*<version>~
                if current_fg:
                    groups_report.append(current_fg)
                current_fg = FunctionalGroupAckDetail(
                    functional_code=seg.get(1),
                    group_control_number=seg.get(2),
                    version=seg.get(3, "004010"),
                )

            elif tag == "AK2":
                # AK2*<doc_type>*<tx_ctrl>~
                current_tx_ack = TransactionAckDetail(
                    doc_type=seg.get(1),
                    control_number=seg.get(2),
                    status="A",
                )
                if current_fg:
                    current_fg.transactions.append(current_tx_ack)

            elif tag == "AK3":
                # AK3*<seg_id>*<seg_pos>*<loop_id>*<error_code>~
                if current_tx_ack:
                    err = EdiSyntaxErrorInfo(
                        segment_tag=seg.get(1),
                        segment_position=int(seg.get(2, "0")) if seg.get(2, "").isdigit() else None,
                        loop_id=seg.get(3) or None,
                        segment_error_code=seg.get(4) or None,
                        error_message=X12_AK3_ERROR_CODES.get(seg.get(4, ""), "Segment error"),
                    )
                    current_tx_ack.syntax_errors.append(err)

            elif tag == "AK4":
                # AK4*<elem_pos>*<ref_num>*<error_code>*<bad_val>~
                if current_tx_ack:
                    pos_raw = seg.get(1)
                    elem_p = int(pos_raw) if pos_raw.isdigit() else None
                    err = EdiSyntaxErrorInfo(
                        element_position=elem_p,
                        element_error_code=seg.get(3) or None,
                        bad_data_value=seg.get(4) or None,
                        error_message=X12_AK4_ERROR_CODES.get(seg.get(3, ""), "Data element error"),
                    )
                    current_tx_ack.syntax_errors.append(err)

            elif tag == "AK5":
                # AK5*<status_code>*<err1>*<err2>...~
                if current_tx_ack:
                    code = seg.get(1, "A").upper()
                    current_tx_ack.status = code
                    current_tx_ack.status_description = X12_AK5_STATUS_CODES.get(code, code)
                    # Collect error codes AK502 - AK506
                    err_codes = [seg.get(i) for i in range(2, len(seg.elements) + 1) if seg.get(i)]
                    current_tx_ack.error_codes = err_codes
                    current_tx_ack.status_description = X12_AK5_STATUS_CODES.get(code, code)

            elif tag == "AK9":
                # AK9*<status>*<inc>*<rcv>*<acc>*<err1>...~
                if current_fg:
                    g_status = seg.get(1, "A").upper()
                    current_fg.status = g_status
                    current_fg.status_description = X12_AK9_STATUS_CODES.get(g_status, g_status)
                    current_fg.included_tx_count = int(seg.get(2, "1")) if seg.get(2, "").isdigit() else 1
                    current_fg.received_tx_count = int(seg.get(3, "1")) if seg.get(3, "").isdigit() else 1
                    current_fg.accepted_tx_count = int(seg.get(4, "1")) if seg.get(4, "").isdigit() else 1
                    current_fg.syntax_error_codes = [seg.get(i) for i in range(5, len(seg.elements) + 1) if seg.get(i)]

        if current_fg:
            groups_report.append(current_fg)

    # Determine overall ACK status
    statuses = [g.status for g in groups_report]
    if all(s == "A" for s in statuses):
        overall_status = "ACCEPTED"
    elif any(s == "R" for s in statuses) and any(s in ("A", "E") for s in statuses):
        overall_status = "PARTIALLY_ACCEPTED"
    elif all(s == "R" for s in statuses):
        overall_status = "REJECTED"
    elif any(s == "E" for s in statuses):
        overall_status = "ACCEPTED_WITH_ERRORS"

    ack_ctrl = interchange.control_number
    ref_ctrl = groups_report[0].group_control_number if groups_report else None

    return ParsedAckReport(
        standard="ANSI_X12",
        ack_type="997",
        sender_id=interchange.sender_id,
        receiver_id=interchange.receiver_id,
        control_number=ack_ctrl,
        ack_status=overall_status,
        acknowledged_control_number=ref_ctrl,
        groups=groups_report,
        messages=[],
        raw_payload=raw_str,
    )


def parse_contrl_ack(raw_contrl: Union[str, EdiInterchange]) -> ParsedAckReport:
    """
    Parses an inbound UN/EDIFACT CONTRL document into a structured ParsedAckReport.
    Extracts UCI, UCM, UCS, and UCD segments.
    """
    if isinstance(raw_contrl, str):
        interchange = parse_edifact(raw_contrl)
        raw_str = raw_contrl
    else:
        interchange = raw_contrl
        raw_str = serialize_edifact(interchange)

    messages_report: List[TransactionAckDetail] = []
    acknowledged_ctrl = None
    uci_status = "7"

    all_txs = interchange.all_transactions()
    for tx in all_txs:
        current_msg: Optional[TransactionAckDetail] = None

        for seg in tx.segments:
            tag = seg.tag

            if tag == "UCI":
                # UCI+<inbound_ctrl>+<sender>+<receiver>+<action_code>+<err_code>'
                acknowledged_ctrl = seg.get(1)
                uci_status = seg.get(4, "7")

            elif tag == "UCM":
                # UCM+<msg_ref>+<msg_type>+<action_code>+<err_code>'
                msg_ref = seg.get(1)
                msg_type_comp = seg.get_composite(2)
                doc_type = msg_type_comp[0] if msg_type_comp else seg.get(2)
                action_code = seg.get(3, "7")
                err_code = seg.get(4)

                current_msg = TransactionAckDetail(
                    doc_type=doc_type,
                    control_number=msg_ref,
                    status=action_code,
                    status_description=EDIFACT_UCM_ACTION_CODES.get(action_code, action_code),
                    error_codes=[err_code] if err_code else [],
                )
                messages_report.append(current_msg)

            elif tag == "UCS":
                # UCS+<seg_pos>+<err_code>'
                if current_msg:
                    pos = int(seg.get(1, "0")) if seg.get(1, "").isdigit() else None
                    code = seg.get(2)
                    current_msg.syntax_errors.append(
                        EdiSyntaxErrorInfo(
                            segment_position=pos,
                            segment_error_code=code,
                            error_message=EDIFACT_UCS_ERROR_CODES.get(code, "Segment syntax error"),
                        )
                    )

            elif tag == "UCD":
                # UCD+<err_code>+<pos:comp>'
                if current_msg:
                    code = seg.get(1)
                    pos_comp = seg.get_composite(2)
                    elem_p = int(pos_comp[0]) if pos_comp and pos_comp[0].isdigit() else None
                    comp_p = int(pos_comp[1]) if len(pos_comp) > 1 and pos_comp[1].isdigit() else None
                    current_msg.syntax_errors.append(
                        EdiSyntaxErrorInfo(
                            element_position=elem_p,
                            component_position=comp_p,
                            element_error_code=code,
                            error_message=EDIFACT_UCD_ERROR_CODES.get(code, "Data element syntax error"),
                        )
                    )

    if uci_status == "7":
        overall_status = "ACCEPTED"
    elif uci_status == "8":
        overall_status = "ACCEPTED_WITH_ERRORS"
    else:
        overall_status = "REJECTED"

    return ParsedAckReport(
        standard="EDIFACT",
        ack_type="CONTRL",
        sender_id=interchange.sender_id,
        receiver_id=interchange.receiver_id,
        control_number=interchange.control_number,
        ack_status=overall_status,
        acknowledged_control_number=acknowledged_ctrl,
        groups=[],
        messages=messages_report,
        raw_payload=raw_str,
    )


def parse_edi_ack(raw_ack: str) -> ParsedAckReport:
    """
    Universal ACK parser that auto-detects standard (ANSI X12 997 vs EDIFACT CONTRL)
    and returns a normalized ParsedAckReport.
    """
    std = detect_edi_standard(raw_ack)
    if std == EdiStandard.EDIFACT:
        return parse_contrl_ack(raw_ack)
    return parse_997_ack(raw_ack)


# ===========================================================================
# 7. EdiAckService Class (Database Persistence & Workflow Automation)
# ===========================================================================

class EdiAckService(CrudService):
    """
    Service managing generation, persistence, and correlation of EDI Functional Acknowledgments.
    Integrates with table T0126 (EDI Transactions) and supports multi-tenant scoping.
    """

    def __init__(self, repo=None, partner_repo=None):
        repo = repo or EDI_TRANSACTION_REPO
        super().__init__(repo)
        self.partner_repo = partner_repo or EDI_PARTNER_REPO

    def get_next_ack_control_number(self, conn=None) -> str:
        """
        Fetches the next atomic control number from database sequence `seq_edi_control_num`
        or generates a timestamp-based sequence fallback.
        """
        serial_val = None

        def _fetch_nextval(c):
            with c.cursor() as cur:
                cur.execute('SELECT nextval(\'"Nova".seq_edi_control_num\')')
                row = cur.fetchone()
                return row[0] if row else None

        if conn is not None:
            try:
                serial_val = _fetch_nextval(conn)
            except Exception as e:
                logger.warning(f"Error fetching nextval from seq_edi_control_num: {e}")
        else:
            try:
                c = get_connection()
                try:
                    serial_val = _fetch_nextval(c)
                finally:
                    release_connection(c)
            except Exception as e:
                logger.warning(f"Error acquiring connection for seq_edi_control_num: {e}")

        if serial_val is None:
            import time
            serial_val = int(time.time() * 1000) % 1000000000

        return str(serial_val)

    def create_and_record_ack(
        self,
        transaction_id: int,
        is_accepted: bool = True,
        errors: Optional[Union[List[EdiSyntaxErrorInfo], Dict[str, List[EdiSyntaxErrorInfo]]]] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generates a Functional Acknowledgment (997 FA or CONTRL) for an inbound EDI transaction record,
        updates the inbound transaction's ack_status and ack_payload in table T0126, and logs the outbound
        ACK transaction.
        
        Args:
            transaction_id: Inbound EDI transaction ID from table T0126.
            is_accepted: Acceptance flag.
            errors: Optional syntax or business rule error details.
            conn: Optional database connection.
            tenant_id: Tenant context override.
            
        Returns:
            Dict containing the updated transaction and generated ACK payload.
        """
        if tenant_id is None:
            tenant_id = get_current_tenant()

        kwargs = {"conn": conn} if conn is not None else {}
        inbound_tx = self.repo.get(transaction_id, **kwargs)
        if not inbound_tx:
            raise ValueError(f"EDI transaction record not found: {transaction_id}")

        raw_payload = inbound_tx.get("raw_payload", "")
        if not raw_payload:
            raise ValueError(f"EDI transaction {transaction_id} contains no raw payload")

        partner_id = inbound_tx.get("partner_id")
        partner = None
        if partner_id:
            try:
                partner = self.partner_repo.get(partner_id, **kwargs)
            except Exception as e:
                logger.warning(f"Could not load partner {partner_id}: {e}")

        ack_ctrl_num = self.get_next_ack_control_number(conn=conn)
        ack_payload, ack_status_enum, summary = generate_edi_ack(
            inbound=raw_payload,
            partner=partner,
            standard=inbound_tx.get("standard"),
            is_accepted=is_accepted,
            errors=errors,
            ack_control_number=ack_ctrl_num,
        )

        # Update inbound transaction with generated ACK
        update_data = {
            "ack_status": ack_status_enum.value,
            "ack_payload": ack_payload,
        }
        updated_inbound = self.repo.update(transaction_id, update_data, **kwargs)

        # Record outbound ACK transaction in T0126
        std_str = summary["standard"]
        doc_type = summary["document_type"]
        outbound_ack_record = {
            "transaction_number": f"ACK-{ack_ctrl_num[-6:]}",
            "partner_id": partner_id,
            "standard": std_str,
            "document_type": doc_type,
            "direction": EdiDirection.OUTBOUND.value,
            "control_number": ack_ctrl_num,
            "status": "PROCESSED",
            "raw_payload": ack_payload,
            "parsed_data": summary,
            "ack_status": EdiAckStatus.ACCEPTED.value,
            "processed_at": datetime.now(timezone.utc),
        }
        try:
            self.repo.create(outbound_ack_record, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to record outbound ACK transaction in T0126: {e}")

        return {
            "inbound_transaction_id": transaction_id,
            "ack_status": ack_status_enum.value,
            "ack_document_type": doc_type,
            "ack_control_number": ack_ctrl_num,
            "ack_payload": ack_payload,
            "summary": summary,
            "updated_transaction": updated_inbound,
        }

    def process_inbound_ack(
        self,
        raw_ack: str,
        partner_id: Optional[int] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Parses an incoming 997 FA or CONTRL acknowledgment from an external partner,
        matches it to the original outbound transaction via control number, and updates
        the transaction status in table T0126.
        """
        if tenant_id is None:
            tenant_id = get_current_tenant()

        parsed_report = parse_edi_ack(raw_ack)
        target_ctrl = parsed_report.acknowledged_control_number or parsed_report.control_number

        kwargs = {"conn": conn} if conn is not None else {}
        matched_tx = None

        if target_ctrl:
            # Query outbound transactions matching control number
            filters: Dict[str, Any] = {
                "direction": EdiDirection.OUTBOUND.value,
                "control_number": target_ctrl,
            }
            if partner_id:
                filters["partner_id"] = partner_id

            candidates = self.repo.list(filters=filters, limit=1, **kwargs)
            if candidates:
                matched_tx = candidates[0]

        if matched_tx:
            self.repo.update(
                matched_tx["id"],
                {
                    "ack_status": parsed_report.ack_status,
                    "ack_payload": raw_ack,
                    "status": "ACKNOWLEDGED" if parsed_report.ack_status == "ACCEPTED" else "FAILED",
                },
                **kwargs,
            )

        return {
            "status": "PROCESSED",
            "ack_report": parsed_report.model_dump(),
            "matched_transaction_id": matched_tx["id"] if matched_tx else None,
        }


# Default singleton instance
edi_ack_service = EdiAckService()
