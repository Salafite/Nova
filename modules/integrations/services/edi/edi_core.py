"""
Nova ERP — Bidirectional ANSI X12 and UN/EDIFACT Syntax Engine
Provides tokenizers, segment parsers, loop extractors, and serial builders
supporting ANSI X12 (ISA, GS, ST, SE, GE, IEA) and UN/EDIFACT (UNB, UNH, UNT, UNZ).
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from modules.integrations.models.edi import EdiStandard, EdiDocumentType


class EdiSyntaxError(Exception):
    """Raised when an EDI document fails syntax parsing or integrity checks."""
    def __init__(self, message: str, segment_index: Optional[int] = None, raw_segment: Optional[str] = None):
        self.message = message
        self.segment_index = segment_index
        self.raw_segment = raw_segment
        super().__init__(f"EDI Syntax Error: {message}" + (f" (segment #{segment_index}: {raw_segment})" if segment_index is not None else ""))


# ---------------------------------------------------------------------------
# Delimiters Configuration
# ---------------------------------------------------------------------------

class EdiDelimiters(BaseModel):
    """
    Delimiter definition for EDI interchanges.
    ANSI X12 standard default: element=* subelement=> segment=~
    UN/EDIFACT standard default: element=+ component=: segment=' release=?
    """
    segment_terminator: str = "~"
    element_separator: str = "*"
    subelement_separator: str = ">"
    release_character: Optional[str] = None
    repetition_separator: Optional[str] = None
    decimal_mark: str = "."

    @classmethod
    def x12_default(cls) -> "EdiDelimiters":
        return cls(
            segment_terminator="~",
            element_separator="*",
            subelement_separator=">",
            release_character=None,
            repetition_separator="^",
            decimal_mark=".",
        )

    @classmethod
    def edifact_default(cls) -> "EdiDelimiters":
        return cls(
            segment_terminator="'",
            element_separator="+",
            subelement_separator=":",
            release_character="?",
            repetition_separator=" ",
            decimal_mark=".",
        )

    @classmethod
    def from_partner(cls, partner: Any) -> "EdiDelimiters":
        """Build delimiters configuration from an EdiPartner model or dict."""
        if isinstance(partner, dict):
            standard = partner.get("edi_standard", "ANSI_X12")
            seg = partner.get("segment_terminator")
            elem = partner.get("element_separator")
            subelem = partner.get("subelement_separator")
            rel = partner.get("release_character")
        else:
            standard = getattr(partner, "edi_standard", "ANSI_X12")
            seg = getattr(partner, "segment_terminator", None)
            elem = getattr(partner, "element_separator", None)
            subelem = getattr(partner, "subelement_separator", None)
            rel = getattr(partner, "release_character", None)

        if standard == EdiStandard.EDIFACT or standard == "EDIFACT":
            default = cls.edifact_default()
            return cls(
                segment_terminator=seg or default.segment_terminator,
                element_separator=elem or default.element_separator,
                subelement_separator=subelem or default.subelement_separator,
                release_character=rel if rel is not None else default.release_character,
                repetition_separator=" ",
                decimal_mark=".",
            )
        else:
            default = cls.x12_default()
            return cls(
                segment_terminator=seg or default.segment_terminator,
                element_separator=elem or default.element_separator,
                subelement_separator=subelem or default.subelement_separator,
                release_character=rel,
                repetition_separator="^",
                decimal_mark=".",
            )


# ---------------------------------------------------------------------------
# Core EDI Segment Model
# ---------------------------------------------------------------------------

class EdiSegment:
    """
    Represents a single parsed or constructed EDI segment.
    Elements are stored in a 0-indexed list representing data elements after the segment tag.
    Helper methods use standard 1-based indexing for EDI specification compliance.
    """

    def __init__(self, tag: str, elements: Optional[List[Union[str, List[str]]]] = None):
        self.tag: str = tag.strip().upper()
        # elements: list where element[0] is element 1 (e.g. BEG01, BGM01)
        self.elements: List[Union[str, List[str]]] = []
        if elements:
            for el in elements:
                if isinstance(el, list):
                    self.elements.append([str(c) for c in el])
                elif el is None:
                    self.elements.append("")
                else:
                    self.elements.append(str(el))

    def __repr__(self) -> str:
        return f"<EdiSegment {self.tag} elements={len(self.elements)}>"

    def __len__(self) -> int:
        return len(self.elements)

    def get(self, pos: int, default: str = "") -> str:
        """
        Get element by 1-based position (e.g. pos=1 returns element 1).
        If the element is composite, returns the first component or joined string.
        """
        if pos < 1 or pos > len(self.elements):
            return default
        val = self.elements[pos - 1]
        if isinstance(val, list):
            return val[0] if val else default
        return str(val) if val is not None else default

    def get_element(self, pos: int, default: str = "") -> str:
        """Alias for get(pos, default)."""
        return self.get(pos, default)

    def get_composite(self, pos: int) -> List[str]:
        """Get element as a list of composite components (1-based index)."""
        if pos < 1 or pos > len(self.elements):
            return []
        val = self.elements[pos - 1]
        if isinstance(val, list):
            return val
        return [str(val)] if val != "" else []

    def get_component(self, pos: int, comp_pos: int, default: str = "") -> str:
        """
        Get a specific subelement/component at 1-based positions.
        pos: element position (1-based)
        comp_pos: component position within element (1-based)
        """
        if pos < 1 or pos > len(self.elements):
            return default
        val = self.elements[pos - 1]
        if isinstance(val, list):
            if comp_pos < 1 or comp_pos > len(val):
                return default
            return str(val[comp_pos - 1])
        elif comp_pos == 1:
            return str(val)
        return default

    def set_element(self, pos: int, value: Union[str, List[str]]) -> "EdiSegment":
        """Set element value at 1-based position, padding with empty strings if needed."""
        if pos < 1:
            raise ValueError("Position must be 1 or greater")
        while len(self.elements) < pos:
            self.elements.append("")
        if isinstance(value, list):
            self.elements[pos - 1] = [str(c) for c in value]
        elif value is None:
            self.elements[pos - 1] = ""
        else:
            self.elements[pos - 1] = str(value)
        return self

    def set_component(self, pos: int, comp_pos: int, value: str) -> "EdiSegment":
        """Set component value inside a composite element at 1-based positions."""
        if pos < 1 or comp_pos < 1:
            raise ValueError("Positions must be 1 or greater")
        while len(self.elements) < pos:
            self.elements.append("")
        current = self.elements[pos - 1]
        if not isinstance(current, list):
            current = [current] if current != "" else []
        while len(current) < comp_pos:
            current.append("")
        current[comp_pos - 1] = str(value) if value is not None else ""
        self.elements[pos - 1] = current
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "elements": self.elements,
        }

    def format_string(self, delimiters: EdiDelimiters) -> str:
        """Serialize segment to a string without segment terminator."""
        parts = [self.tag]
        # Trim trailing empty elements for cleaner EDI output
        trimmed_elements = list(self.elements)
        while trimmed_elements and (trimmed_elements[-1] == "" or trimmed_elements[-1] == []):
            trimmed_elements.pop()

        for el in trimmed_elements:
            if isinstance(el, list):
                # Composite element
                escaped_comps = [
                    _escape_edifact(c, delimiters) if delimiters.release_character else c
                    for c in el
                ]
                parts.append(delimiters.subelement_separator.join(escaped_comps))
            else:
                s = str(el)
                if delimiters.release_character:
                    s = _escape_edifact(s, delimiters)
                parts.append(s)

        return delimiters.element_separator.join(parts)


# ---------------------------------------------------------------------------
# Transaction Set / Message Model
# ---------------------------------------------------------------------------

class EdiTransactionSet:
    """
    Represents a single business document transaction set (e.g. ANSI X12 850 / 856 / 810)
    or EDIFACT Message (e.g. ORDERS / DESADV / INVOIC).
    """

    def __init__(
        self,
        doc_type: str,
        control_number: str = "",
        standard: str = "ANSI_X12",
        segments: Optional[List[EdiSegment]] = None,
        functional_group_code: Optional[str] = None,
    ):
        self.doc_type: str = doc_type.strip()
        self.control_number: str = control_number.strip()
        self.standard: str = standard.strip()
        self.functional_group_code: Optional[str] = functional_group_code
        self.segments: List[EdiSegment] = segments or []

    def __repr__(self) -> str:
        return f"<EdiTransactionSet type={self.doc_type} ctrl={self.control_number} segments={len(self.segments)}>"

    def add_segment(self, tag: str, *elements: Any) -> EdiSegment:
        """Create and append a segment to this transaction set."""
        seg = EdiSegment(tag, list(elements))
        self.segments.append(seg)
        return seg

    def find_segments(self, tag: str) -> List[EdiSegment]:
        """Find all segments matching tag."""
        target = tag.strip().upper()
        return [seg for seg in self.segments if seg.tag == target]

    def find_first(self, tag: str) -> Optional[EdiSegment]:
        """Find the first segment matching tag."""
        target = tag.strip().upper()
        for seg in self.segments:
            if seg.tag == target:
                return seg
        return None

    def get_loops(self, start_tag: str, stop_tags: Optional[List[str]] = None) -> List[List[EdiSegment]]:
        """
        Group segments into loops starting with `start_tag` until the next `start_tag`
        or any tag in `stop_tags`.
        Example: get_loops('PO1') extracts all line item loops in an 850 PO.
        Example: get_loops('LIN') extracts all line item loops in an EDIFACT ORDERS.
        """
        start = start_tag.strip().upper()
        stops = [s.strip().upper() for s in (stop_tags or [])]
        loops: List[List[EdiSegment]] = []
        current_loop: Optional[List[EdiSegment]] = None

        for seg in self.segments:
            if seg.tag == start:
                if current_loop is not None:
                    loops.append(current_loop)
                current_loop = [seg]
            elif current_loop is not None:
                if seg.tag in stops:
                    loops.append(current_loop)
                    current_loop = None
                else:
                    current_loop.append(seg)

        if current_loop is not None:
            loops.append(current_loop)

        return loops

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard": self.standard,
            "doc_type": self.doc_type,
            "control_number": self.control_number,
            "functional_group_code": self.functional_group_code,
            "segments": [seg.to_dict() for seg in self.segments],
        }


# ---------------------------------------------------------------------------
# Functional Group Model (X12 GS/GE)
# ---------------------------------------------------------------------------

class EdiFunctionalGroup:
    """
    Represents an ANSI X12 Functional Group (GS/GE envelope) or EDIFACT Group.
    """

    def __init__(
        self,
        functional_code: str = "",
        sender_code: str = "",
        receiver_code: str = "",
        group_date: str = "",
        group_time: str = "",
        group_control_number: str = "",
        agency_code: str = "X",
        version: str = "004010",
        transactions: Optional[List[EdiTransactionSet]] = None,
    ):
        self.functional_code: str = functional_code.strip()
        self.sender_code: str = sender_code.strip()
        self.receiver_code: str = receiver_code.strip()
        self.group_date: str = group_date.strip()
        self.group_time: str = group_time.strip()
        self.group_control_number: str = group_control_number.strip()
        self.agency_code: str = agency_code.strip()
        self.version: str = version.strip()
        self.transactions: List[EdiTransactionSet] = transactions or []

    def __repr__(self) -> str:
        return f"<EdiFunctionalGroup code={self.functional_code} ctrl={self.group_control_number} txs={len(self.transactions)}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "functional_code": self.functional_code,
            "sender_code": self.sender_code,
            "receiver_code": self.receiver_code,
            "group_date": self.group_date,
            "group_time": self.group_time,
            "group_control_number": self.group_control_number,
            "agency_code": self.agency_code,
            "version": self.version,
            "transactions": [tx.to_dict() for tx in self.transactions],
        }


# ---------------------------------------------------------------------------
# Interchange Envelope Model (ISA/IEA or UNB/UNZ)
# ---------------------------------------------------------------------------

class EdiInterchange:
    """
    Represents an entire EDI Interchange document containing envelopes, groups,
    and business transaction messages.
    """

    def __init__(
        self,
        standard: str = "ANSI_X12",
        sender_id: str = "",
        sender_qualifier: str = "ZZ",
        receiver_id: str = "",
        receiver_qualifier: str = "ZZ",
        control_number: str = "1",
        interchange_date: str = "",
        interchange_time: str = "",
        is_test: bool = False,
        delimiters: Optional[EdiDelimiters] = None,
        groups: Optional[List[EdiFunctionalGroup]] = None,
        messages: Optional[List[EdiTransactionSet]] = None,
        raw_segments: Optional[List[EdiSegment]] = None,
    ):
        self.standard: str = standard.strip()
        self.sender_id: str = sender_id.strip()
        self.sender_qualifier: str = sender_qualifier.strip()
        self.receiver_id: str = receiver_id.strip()
        self.receiver_qualifier: str = receiver_qualifier.strip()
        self.control_number: str = control_number.strip()
        self.interchange_date: str = interchange_date.strip()
        self.interchange_time: str = interchange_time.strip()
        self.is_test: bool = is_test
        self.delimiters: EdiDelimiters = delimiters or (
            EdiDelimiters.edifact_default() if standard == "EDIFACT" else EdiDelimiters.x12_default()
        )
        self.groups: List[EdiFunctionalGroup] = groups or []
        self.messages: List[EdiTransactionSet] = messages or []
        self.raw_segments: List[EdiSegment] = raw_segments or []

    def __repr__(self) -> str:
        return f"<EdiInterchange standard={self.standard} sender={self.sender_id} receiver={self.receiver_id} ctrl={self.control_number}>"

    def all_transactions(self) -> List[EdiTransactionSet]:
        """Returns all transaction sets / messages contained across all groups or standalone."""
        txs: List[EdiTransactionSet] = []
        if self.groups:
            for g in self.groups:
                txs.extend(g.transactions)
        if self.messages:
            for m in self.messages:
                if m not in txs:
                    txs.append(m)
        return txs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard": self.standard,
            "sender_id": self.sender_id,
            "sender_qualifier": self.sender_qualifier,
            "receiver_id": self.receiver_id,
            "receiver_qualifier": self.receiver_qualifier,
            "control_number": self.control_number,
            "interchange_date": self.interchange_date,
            "interchange_time": self.interchange_time,
            "is_test": self.is_test,
            "groups": [g.to_dict() for g in self.groups],
            "messages": [m.to_dict() for m in self.messages],
        }


# ---------------------------------------------------------------------------
# Escaping and Utility Functions
# ---------------------------------------------------------------------------

def _escape_edifact(text: str, delimiters: EdiDelimiters) -> str:
    """Escapes EDIFACT delimiters with release character (default ?)."""
    rel = delimiters.release_character
    if not rel:
        return text
    chars_to_escape = [rel, delimiters.segment_terminator, delimiters.element_separator, delimiters.subelement_separator]
    out = []
    for ch in text:
        if ch in chars_to_escape:
            out.append(rel)
        out.append(ch)
    return "".join(out)


def _split_edifact_tokens(raw: str, delimiter: str, release_char: Optional[str] = "?") -> List[str]:
    """
    Splits string by delimiter while respecting the EDIFACT release character.
    Example: splitting "ABC?+DEF+GHI" by "+" returns ["ABC?+DEF", "GHI"].
    """
    if not release_char or release_char not in raw:
        return raw.split(delimiter)

    tokens: List[str] = []
    current: List[str] = []
    i = 0
    length = len(raw)
    while i < length:
        ch = raw[i]
        if ch == release_char and i + 1 < length:
            # Escape sequence: keep the escaped char
            current.append(ch)
            current.append(raw[i + 1])
            i += 2
            continue
        elif ch == delimiter:
            tokens.append("".join(current))
            current = []
            i += 1
            continue
        else:
            current.append(ch)
            i += 1

    tokens.append("".join(current))
    return tokens


def _unescape_edifact(text: str, release_char: Optional[str] = "?") -> str:
    """Removes release characters that were escaping special delimiters."""
    if not release_char or release_char not in text:
        return text
    out: List[str] = []
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == release_char and i + 1 < length:
            out.append(text[i + 1])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Standard Detection
# ---------------------------------------------------------------------------

def detect_edi_standard(raw_content: str) -> EdiStandard:
    """
    Detect whether raw EDI content is ANSI X12 or UN/EDIFACT.
    """
    stripped = raw_content.strip()
    if stripped.startswith("ISA") or stripped.startswith("GS") or stripped.startswith("ST"):
        return EdiStandard.ANSI_X12
    if stripped.startswith("UNA") or stripped.startswith("UNB") or stripped.startswith("UNH"):
        return EdiStandard.EDIFACT
    # Check for prevalent delimiters
    if "+" in stripped and ":" in stripped and "'" in stripped:
        return EdiStandard.EDIFACT
    if "*" in stripped and "~" in stripped:
        return EdiStandard.ANSI_X12
    # Default fallback
    return EdiStandard.ANSI_X12


# ---------------------------------------------------------------------------
# ANSI X12 Parser
# ---------------------------------------------------------------------------

def parse_x12(raw_content: str, delimiters: Optional[EdiDelimiters] = None) -> EdiInterchange:
    """
    Parse an ANSI X12 EDI document into an EdiInterchange structure.
    Auto-detects delimiters from the ISA segment if not explicitly provided.
    """
    content = raw_content.strip()
    if not content:
        raise EdiSyntaxError("EDI content is empty")

    # Delimiter auto-detection from ISA segment
    elem_sep = "*"
    seg_term = "~"
    subelem_sep = ">"

    if content.startswith("ISA"):
        if len(content) >= 4:
            elem_sep = content[3]
        if len(content) >= 106 and content[103:104] != "":
            # Standard X12 ISA is exactly 106 characters long
            subelem_sep = content[104]  # ISA16
            seg_term = content[105]     # Segment terminator
        elif delimiters:
            seg_term = delimiters.segment_terminator
            elem_sep = delimiters.element_separator
            subelem_sep = delimiters.subelement_separator
    elif delimiters:
        seg_term = delimiters.segment_terminator
        elem_sep = delimiters.element_separator
        subelem_sep = delimiters.subelement_separator

    active_delims = EdiDelimiters(
        segment_terminator=seg_term,
        element_separator=elem_sep,
        subelement_separator=subelem_sep,
        release_character=None,
        repetition_separator="^",
    )

    # Split into segments
    raw_segments = []
    raw_pieces = content.split(seg_term)
    for piece in raw_pieces:
        p = piece.strip()
        if p:
            raw_segments.append(p)

    if not raw_segments:
        raise EdiSyntaxError("No valid EDI segments found in content")

    # Tokenize each segment
    parsed_segments: List[EdiSegment] = []
    has_valid_envelope = False
    for idx, raw_seg in enumerate(raw_segments):
        parts = raw_seg.split(elem_sep)
        tag = parts[0].strip().upper()
        if tag in ("ISA", "GS", "ST"):
            has_valid_envelope = True
        raw_elements = parts[1:]
        elements: List[Union[str, List[str]]] = []
        for el in raw_elements:
            # Check for subelement separator if present and not in ISA
            if tag != "ISA" and subelem_sep and subelem_sep in el:
                elements.append(el.split(subelem_sep))
            else:
                elements.append(el)
        parsed_segments.append(EdiSegment(tag, elements))

    if not has_valid_envelope:
        raise EdiSyntaxError("Invalid ANSI X12 document: missing ISA, GS, or ST envelope segment")

    # Construct Hierarchical Interchange -> Groups -> Transaction Sets
    interchange = EdiInterchange(
        standard="ANSI_X12",
        delimiters=active_delims,
        raw_segments=parsed_segments,
    )

    current_group: Optional[EdiFunctionalGroup] = None
    current_tx: Optional[EdiTransactionSet] = None
    tx_segment_count = 0

    for idx, seg in enumerate(parsed_segments):
        tag = seg.tag

        if tag == "ISA":
            interchange.sender_qualifier = seg.get(5).strip()
            interchange.sender_id = seg.get(6).strip()
            interchange.receiver_qualifier = seg.get(7).strip()
            interchange.receiver_id = seg.get(8).strip()
            interchange.interchange_date = seg.get(9).strip()
            interchange.interchange_time = seg.get(10).strip()
            interchange.control_number = seg.get(13).strip()
            interchange.is_test = (seg.get(15).strip().upper() == "T")

        elif tag == "GS":
            current_group = EdiFunctionalGroup(
                functional_code=seg.get(1).strip(),
                sender_code=seg.get(2).strip(),
                receiver_code=seg.get(3).strip(),
                group_date=seg.get(4).strip(),
                group_time=seg.get(5).strip(),
                group_control_number=seg.get(6).strip(),
                agency_code=seg.get(7).strip(),
                version=seg.get(8).strip(),
            )
            interchange.groups.append(current_group)

        elif tag == "ST":
            doc_type = seg.get(1).strip()
            tx_ctrl = seg.get(2).strip()
            current_tx = EdiTransactionSet(
                doc_type=doc_type,
                control_number=tx_ctrl,
                standard="ANSI_X12",
                functional_group_code=current_group.functional_code if current_group else None,
                segments=[seg],
            )
            tx_segment_count = 1
            if current_group:
                current_group.transactions.append(current_tx)
            else:
                interchange.messages.append(current_tx)

        elif tag == "SE":
            if current_tx:
                current_tx.segments.append(seg)
                tx_segment_count += 1
                expected_count = int(seg.get(1, "0") or "0")
                if expected_count > 0 and expected_count != tx_segment_count:
                    pass
                current_tx = None
            else:
                raise EdiSyntaxError("SE segment without preceding ST", segment_index=idx, raw_segment=seg.tag)

        elif tag == "GE":
            if current_group:
                current_group = None

        elif tag == "IEA":
            # End of interchange
            pass

        else:
            # Normal data segment
            if current_tx:
                current_tx.segments.append(seg)
                tx_segment_count += 1
            else:
                # Top-level or outside transaction segment
                pass

    return interchange


# ---------------------------------------------------------------------------
# UN/EDIFACT Parser
# ---------------------------------------------------------------------------

def parse_edifact(raw_content: str, delimiters: Optional[EdiDelimiters] = None) -> EdiInterchange:
    """
    Parse a UN/EDIFACT EDI document into an EdiInterchange structure.
    Auto-detects delimiters from UNA Service String Advice if present.
    """
    content = raw_content.strip()
    if not content:
        raise EdiSyntaxError("EDI content is empty")

    comp_sep = ":"
    elem_sep = "+"
    decimal_mark = "."
    release_char = "?"
    rep_sep = " "
    seg_term = "'"

    if content.startswith("UNA"):
        # UNA is exactly 9 characters long: UNA:+.? '
        if len(content) >= 9:
            comp_sep = content[3]
            elem_sep = content[4]
            decimal_mark = content[5]
            release_char = content[6] if content[6] != " " else None
            rep_sep = content[7]
            seg_term = content[8]
            # Strip UNA prefix
            content = content[9:].strip()
    elif delimiters:
        comp_sep = delimiters.subelement_separator
        elem_sep = delimiters.element_separator
        decimal_mark = delimiters.decimal_mark
        release_char = delimiters.release_character
        rep_sep = delimiters.repetition_separator or " "
        seg_term = delimiters.segment_terminator

    active_delims = EdiDelimiters(
        segment_terminator=seg_term,
        element_separator=elem_sep,
        subelement_separator=comp_sep,
        release_character=release_char,
        repetition_separator=rep_sep,
        decimal_mark=decimal_mark,
    )

    # Split segments respecting release characters
    raw_segments = _split_edifact_tokens(content, seg_term, release_char)
    parsed_segments: List[EdiSegment] = []
    has_valid_envelope = False

    for idx, raw_seg in enumerate(raw_segments):
        trimmed = raw_seg.strip()
        if not trimmed:
            continue
        # Split elements by element_separator (+) respecting release_char
        elem_tokens = _split_edifact_tokens(trimmed, elem_sep, release_char)
        tag = elem_tokens[0].strip().upper()
        if tag in ("UNB", "UNH"):
            has_valid_envelope = True
        raw_elements = elem_tokens[1:]

        elements: List[Union[str, List[str]]] = []
        for el in raw_elements:
            if comp_sep and comp_sep in el:
                # Split composite components
                comps = _split_edifact_tokens(el, comp_sep, release_char)
                unescaped_comps = [_unescape_edifact(c, release_char) for c in comps]
                elements.append(unescaped_comps)
            else:
                elements.append(_unescape_edifact(el, release_char))

        parsed_segments.append(EdiSegment(tag, elements))

    if not has_valid_envelope:
        raise EdiSyntaxError("Invalid UN/EDIFACT document: missing UNB or UNH envelope segment")

    # Construct Interchange -> Messages
    interchange = EdiInterchange(
        standard="EDIFACT",
        delimiters=active_delims,
        raw_segments=parsed_segments,
    )

    current_msg: Optional[EdiTransactionSet] = None
    msg_segment_count = 0

    for idx, seg in enumerate(parsed_segments):
        tag = seg.tag

        if tag == "UNB":
            # UNB+UNOA:2+SENDER:ZZ+RECEIVER:ZZ+YYMMDD:HHMM+CTRLNUM'
            sender_comp = seg.get_composite(2)
            interchange.sender_id = sender_comp[0] if sender_comp else seg.get(2)
            interchange.sender_qualifier = sender_comp[1] if len(sender_comp) > 1 else "ZZ"

            rcv_comp = seg.get_composite(3)
            interchange.receiver_id = rcv_comp[0] if rcv_comp else seg.get(3)
            interchange.receiver_qualifier = rcv_comp[1] if len(rcv_comp) > 1 else "ZZ"

            dt_comp = seg.get_composite(4)
            interchange.interchange_date = dt_comp[0] if dt_comp else seg.get(4)
            interchange.interchange_time = dt_comp[1] if len(dt_comp) > 1 else ""

            interchange.control_number = seg.get(5)
            interchange.is_test = (seg.get(11) == "1")

        elif tag == "UNH":
            msg_ref = seg.get(1)
            msg_type_comp = seg.get_composite(2)
            doc_type = msg_type_comp[0] if msg_type_comp else seg.get(2)

            current_msg = EdiTransactionSet(
                doc_type=doc_type,
                control_number=msg_ref,
                standard="EDIFACT",
                segments=[seg],
            )
            msg_segment_count = 1
            interchange.messages.append(current_msg)

        elif tag == "UNT":
            if current_msg:
                current_msg.segments.append(seg)
                msg_segment_count += 1
                current_msg = None
            else:
                raise EdiSyntaxError("UNT segment without preceding UNH", segment_index=idx, raw_segment=seg.tag)

        elif tag == "UNZ":
            # End of interchange
            pass

        else:
            if current_msg:
                current_msg.segments.append(seg)
                msg_segment_count += 1

    return interchange


# ---------------------------------------------------------------------------
# Universal Parser
# ---------------------------------------------------------------------------

def parse_edi(
    raw_content: str,
    standard: Optional[Union[str, EdiStandard]] = None,
    delimiters: Optional[EdiDelimiters] = None,
) -> EdiInterchange:
    """
    Universal parser for EDI documents. Automatically determines standard if not provided.
    """
    if not standard:
        detected = detect_edi_standard(raw_content)
    elif isinstance(standard, EdiStandard):
        detected = standard
    else:
        detected = EdiStandard.EDIFACT if standard.upper() == "EDIFACT" else EdiStandard.ANSI_X12

    if detected == EdiStandard.EDIFACT:
        return parse_edifact(raw_content, delimiters)
    else:
        return parse_x12(raw_content, delimiters)


# ---------------------------------------------------------------------------
# ANSI X12 Serializer / Builder
# ---------------------------------------------------------------------------

def serialize_x12(
    interchange: EdiInterchange,
    delimiters: Optional[EdiDelimiters] = None,
    line_breaks: bool = True,
) -> str:
    """
    Serialize an EdiInterchange structure into ANSI X12 formatted text.
    Handles exact padding constraints for ISA envelope segments and computes SE/GE/IEA counts.
    """
    delims = delimiters or interchange.delimiters or EdiDelimiters.x12_default()
    lines: List[str] = []
    term = delims.segment_terminator
    sep = delims.element_separator
    subsep = delims.subelement_separator
    eol = "\n" if line_breaks else ""

    now = datetime.now(timezone.utc)
    i_date = interchange.interchange_date or now.strftime("%y%m%d")
    i_time = interchange.interchange_time or now.strftime("%H%M")
    ctrl_num_9 = str(interchange.control_number or "1").zfill(9)[-9:]

    # ISA Envelope (fixed widths for compliance)
    isa_elements = [
        "00",                         # ISA01: Auth Info Qualifier
        f"{'':10}",                   # ISA02: Auth Info (10 chars)
        "00",                         # ISA03: Security Info Qualifier
        f"{'':10}",                   # ISA04: Security Info (10 chars)
        interchange.sender_qualifier.ljust(2)[:2] or "ZZ",  # ISA05
        interchange.sender_id.ljust(15)[:15],               # ISA06
        interchange.receiver_qualifier.ljust(2)[:2] or "ZZ",# ISA07
        interchange.receiver_id.ljust(15)[:15],             # ISA08
        i_date.ljust(6)[:6],          # ISA09: YYMMDD
        i_time.ljust(4)[:4],          # ISA10: HHMM
        "U",                          # ISA11: Control Standards Identifier
        "00401",                      # ISA12: Version
        ctrl_num_9,                   # ISA13: 9-digit control num
        "0",                          # ISA14: Ack requested
        "T" if interchange.is_test else "P",  # ISA15: Usage indicator
        subsep,                       # ISA16: Component separator
    ]
    isa_seg = f"ISA{sep}{sep.join(isa_elements)}{term}"
    lines.append(isa_seg)

    # Groups
    groups = interchange.groups
    if not groups and interchange.messages:
        # Wrap standalone messages in default group
        default_fg = "PO"
        if interchange.messages and interchange.messages[0].doc_type == "856":
            default_fg = "SH"
        elif interchange.messages and interchange.messages[0].doc_type == "810":
            default_fg = "IN"
        elif interchange.messages and interchange.messages[0].doc_type == "997":
            default_fg = "FA"
        elif interchange.messages and interchange.messages[0].doc_type == "832":
            default_fg = "SC"

        groups = [
            EdiFunctionalGroup(
                functional_code=default_fg,
                sender_code=interchange.sender_id,
                receiver_code=interchange.receiver_id,
                group_date=now.strftime("%Y%m%d"),
                group_time=now.strftime("%H%M"),
                group_control_number=interchange.control_number or "1",
                transactions=interchange.messages,
            )
        ]

    total_groups = len(groups)
    for group_idx, group in enumerate(groups, start=1):
        g_ctrl = group.group_control_number or str(group_idx)
        g_date = group.group_date or now.strftime("%Y%m%d")
        g_time = group.group_time or now.strftime("%H%M")
        gs_elements = [
            group.functional_code or "PO",
            group.sender_code or interchange.sender_id,
            group.receiver_code or interchange.receiver_id,
            g_date,
            g_time,
            g_ctrl,
            group.agency_code or "X",
            group.version or "004010",
        ]
        lines.append(f"GS{sep}{sep.join(gs_elements)}{term}")

        # Transactions
        for tx_idx, tx in enumerate(group.transactions, start=1):
            tx_ctrl = tx.control_number or str(tx_idx).zfill(4)
            # Filter out ST and SE if already in segments to avoid duplicates
            body_segments = [s for s in tx.segments if s.tag not in ("ST", "SE")]
            # Calculate total segments: ST + body + SE = len(body_segments) + 2
            total_tx_segs = len(body_segments) + 2

            lines.append(f"ST{sep}{tx.doc_type}{sep}{tx_ctrl}{term}")
            for seg in body_segments:
                lines.append(f"{seg.format_string(delims)}{term}")
            lines.append(f"SE{sep}{total_tx_segs}{sep}{tx_ctrl}{term}")

        # GE segment: count of transactions in group
        lines.append(f"GE{sep}{len(group.transactions)}{sep}{g_ctrl}{term}")

    # IEA segment: count of functional groups in interchange
    lines.append(f"IEA{sep}{total_groups}{sep}{ctrl_num_9}{term}")

    return eol.join(lines) + (eol if line_breaks else "")


# ---------------------------------------------------------------------------
# UN/EDIFACT Serializer / Builder
# ---------------------------------------------------------------------------

def serialize_edifact(
    interchange: EdiInterchange,
    delimiters: Optional[EdiDelimiters] = None,
    include_una: bool = False,
    line_breaks: bool = True,
) -> str:
    """
    Serialize an EdiInterchange structure into UN/EDIFACT formatted text.
    Handles release character escaping and computes UNT/UNZ counts.
    """
    delims = delimiters or interchange.delimiters or EdiDelimiters.edifact_default()
    lines: List[str] = []
    term = delims.segment_terminator
    sep = delims.element_separator
    subsep = delims.subelement_separator
    rel = delims.release_character or "?"
    dec = delims.decimal_mark or "."
    rep = delims.repetition_separator or " "
    eol = "\n" if line_breaks else ""

    now = datetime.now(timezone.utc)
    i_date = interchange.interchange_date or now.strftime("%y%m%d")
    i_time = interchange.interchange_time or now.strftime("%H%M")
    ctrl_num = str(interchange.control_number or "1")

    # Optional UNA Service String Advice
    if include_una:
        una_str = f"UNA{subsep}{sep}{dec}{rel}{rep}{term}"
        lines.append(una_str)

    # UNB Envelope
    sender_escaped = _escape_edifact(interchange.sender_id, delims)
    sender_qual = _escape_edifact(interchange.sender_qualifier or "ZZ", delims)
    receiver_escaped = _escape_edifact(interchange.receiver_id, delims)
    receiver_qual = _escape_edifact(interchange.receiver_qualifier or "ZZ", delims)

    unb_elements = [
        f"UNOA{subsep}2",
        f"{sender_escaped}{subsep}{sender_qual}",
        f"{receiver_escaped}{subsep}{receiver_qual}",
        f"{i_date}{subsep}{i_time}",
        ctrl_num,
    ]
    if interchange.is_test:
        while len(unb_elements) < 10:
            unb_elements.append("")
        unb_elements.append("1")

    lines.append(f"UNB{sep}{sep.join(unb_elements)}{term}")

    # Messages
    all_msgs = interchange.all_transactions()
    for msg_idx, msg in enumerate(all_msgs, start=1):
        msg_ref = msg.control_number or str(msg_idx)
        body_segments = [s for s in msg.segments if s.tag not in ("UNH", "UNT")]
        # Total segments: UNH + body + UNT = len(body_segments) + 2
        total_msg_segs = len(body_segments) + 2

        # UNH segment: UNH+REF+ORDERS:D:96A:UN:EAN008'
        version_part = f"{msg.doc_type}{subsep}D{subsep}96A{subsep}UN{subsep}EAN008"
        lines.append(f"UNH{sep}{msg_ref}{sep}{version_part}{term}")

        for seg in body_segments:
            lines.append(f"{seg.format_string(delims)}{term}")

        lines.append(f"UNT{sep}{total_msg_segs}{sep}{msg_ref}{term}")

    # UNZ Envelope: UNZ+COUNT+CTRLNUM'
    lines.append(f"UNZ{sep}{len(all_msgs)}{sep}{ctrl_num}{term}")

    return eol.join(lines) + (eol if line_breaks else "")


# ---------------------------------------------------------------------------
# Universal Serializer
# ---------------------------------------------------------------------------

def serialize_edi(
    interchange: EdiInterchange,
    delimiters: Optional[EdiDelimiters] = None,
    line_breaks: bool = True,
) -> str:
    """
    Serialize an EdiInterchange to formatted EDI string matching its standard.
    """
    if interchange.standard == "EDIFACT" or interchange.standard == EdiStandard.EDIFACT:
        return serialize_edifact(interchange, delimiters, include_una=False, line_breaks=line_breaks)
    return serialize_x12(interchange, delimiters, line_breaks=line_breaks)


# ---------------------------------------------------------------------------
# Fluent Builders
# ---------------------------------------------------------------------------

class X12Builder:
    """
    Fluent builder for constructing ANSI X12 interchanges and transaction sets.
    """

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        sender_qualifier: str = "ZZ",
        receiver_qualifier: str = "ZZ",
        control_number: str = "1",
        is_test: bool = False,
        delimiters: Optional[EdiDelimiters] = None,
    ):
        self.delimiters = delimiters or EdiDelimiters.x12_default()
        self.interchange = EdiInterchange(
            standard="ANSI_X12",
            sender_id=sender_id,
            sender_qualifier=sender_qualifier,
            receiver_id=receiver_id,
            receiver_qualifier=receiver_qualifier,
            control_number=control_number,
            is_test=is_test,
            delimiters=self.delimiters,
        )
        self._current_group: Optional[EdiFunctionalGroup] = None
        self._current_tx: Optional[EdiTransactionSet] = None

    def start_group(
        self,
        functional_code: str = "PO",
        group_control_number: str = "1",
        version: str = "004010",
    ) -> "X12Builder":
        self._current_group = EdiFunctionalGroup(
            functional_code=functional_code,
            sender_code=self.interchange.sender_id,
            receiver_code=self.interchange.receiver_id,
            group_control_number=group_control_number,
            version=version,
        )
        self.interchange.groups.append(self._current_group)
        return self

    def start_transaction(self, doc_type: str, control_number: str = "0001") -> "X12Builder":
        if not self._current_group:
            self.start_group(functional_code="PO", group_control_number="1")
        self._current_tx = EdiTransactionSet(
            doc_type=doc_type,
            control_number=control_number,
            standard="ANSI_X12",
            functional_group_code=self._current_group.functional_code if self._current_group else None,
        )
        if self._current_group:
            self._current_group.transactions.append(self._current_tx)
        return self

    def add_segment(self, tag: str, *elements: Any) -> "X12Builder":
        if not self._current_tx:
            raise EdiSyntaxError("Cannot add segment without an active transaction set. Call start_transaction() first.")
        self._current_tx.add_segment(tag, *elements)
        return self

    def end_transaction(self) -> "X12Builder":
        self._current_tx = None
        return self

    def end_group(self) -> "X12Builder":
        self._current_group = None
        return self

    def to_interchange(self) -> EdiInterchange:
        return self.interchange

    def build(self, line_breaks: bool = True) -> str:
        return serialize_x12(self.interchange, self.delimiters, line_breaks=line_breaks)


class EdifactBuilder:
    """
    Fluent builder for constructing UN/EDIFACT interchanges and messages.
    """

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        sender_qualifier: str = "ZZ",
        receiver_qualifier: str = "ZZ",
        control_number: str = "1",
        is_test: bool = False,
        delimiters: Optional[EdiDelimiters] = None,
        include_una: bool = False,
    ):
        self.delimiters = delimiters or EdiDelimiters.edifact_default()
        self.include_una = include_una
        self.interchange = EdiInterchange(
            standard="EDIFACT",
            sender_id=sender_id,
            sender_qualifier=sender_qualifier,
            receiver_id=receiver_id,
            receiver_qualifier=receiver_qualifier,
            control_number=control_number,
            is_test=is_test,
            delimiters=self.delimiters,
        )
        self._current_msg: Optional[EdiTransactionSet] = None

    def start_message(
        self,
        doc_type: Optional[str] = None,
        control_number: str = "1",
        msg_type: Optional[str] = None,
        version: str = "D",
        release: str = "96A",
        agency: str = "UN",
        assoc_code: str = "EAN008",
        **kwargs: Any,
    ) -> "EdifactBuilder":
        effective_doc_type = doc_type or msg_type or "ORDERS"
        effective_ctrl = str(control_number or kwargs.get("message_ref", "1"))
        self._current_msg = EdiTransactionSet(
            doc_type=effective_doc_type,
            control_number=effective_ctrl,
            standard="EDIFACT",
        )
        self.interchange.messages.append(self._current_msg)
        return self

    def add_segment(self, tag: str, *elements: Any) -> "EdifactBuilder":
        if not self._current_msg:
            raise EdiSyntaxError("Cannot add segment without an active message. Call start_message() first.")
        self._current_msg.add_segment(tag, *elements)
        return self

    def end_message(self) -> "EdifactBuilder":
        self._current_msg = None
        return self

    def to_interchange(self) -> EdiInterchange:
        return self.interchange

    def build(self, line_breaks: bool = True) -> str:
        return serialize_edifact(
            self.interchange,
            self.delimiters,
            include_una=self.include_una,
            line_breaks=line_breaks,
        )
