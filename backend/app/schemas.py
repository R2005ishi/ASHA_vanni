"""Structured records for the three visit types.

Every field is optional: the ASHA only says what she observed, and anything
she did not say stays null and is listed in `missing_fields` so the app can
prompt her. We never invent values.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

VisitType = Literal["ANC", "HBNC", "IMMUNISATION"]
Lang = Literal["ta", "hi"]


class PatientRef(BaseModel):
    name: Optional[str] = None
    husband_name: Optional[str] = None   # ANC: husband; HBNC/immunisation: mother's name
    village: Optional[str] = None


class ANCRecord(BaseModel):
    """ANC = Antenatal Care (pregnancy check-up)."""
    gestation_months: Optional[int] = Field(None, ge=1, le=10)
    bp_systolic: Optional[int] = Field(None, ge=60, le=260)
    bp_diastolic: Optional[int] = Field(None, ge=30, le=180)
    bp_status_spoken: Optional[Literal["normal", "high", "low"]] = None  # "BP normal" with no numbers
    hb: Optional[float] = Field(None, ge=2, le=20)                       # Haemoglobin g/dL
    weight_kg: Optional[float] = Field(None, ge=25, le=150)
    ifa_tablets_given: Optional[int] = Field(None, ge=0, le=200)        # IFA = Iron Folic Acid
    calcium_tablets_given: Optional[int] = Field(None, ge=0, le=200)
    td_dose: Optional[Literal["Td1", "Td2", "Td-booster"]] = None        # Td = Tetanus-diphtheria
    complaints: list[str] = []
    next_visit_date: Optional[str] = None                                # YYYY-MM-DD


class HBNCRecord(BaseModel):
    """HBNC = Home-Based Newborn Care."""
    baby_age_days: Optional[int] = Field(None, ge=0, le=60)
    weight_kg: Optional[float] = Field(None, ge=0.5, le=8)
    temperature_c: Optional[float] = Field(None, ge=30, le=43)
    breastfeeding_ok: Optional[bool] = None
    cord_ok: Optional[bool] = None
    complaints: list[str] = []
    next_visit_date: Optional[str] = None


class ImmunisationRecord(BaseModel):
    child_age_weeks: Optional[int] = Field(None, ge=0, le=260)
    vaccines_given: list[str] = []          # canonical names, see normalize.VACCINES
    next_visit_date: Optional[str] = None
    complaints: list[str] = []


RECORD_MODEL = {"ANC": ANCRecord, "HBNC": HBNCRecord, "IMMUNISATION": ImmunisationRecord}

# Fields we prompt the ASHA about when they are missing
EXPECTED_FIELDS = {
    "ANC": ["gestation_months", "bp", "hb", "ifa_tablets_given", "next_visit_date"],
    "HBNC": ["baby_age_days", "weight_kg", "temperature_c", "breastfeeding_ok", "next_visit_date"],
    "IMMUNISATION": ["vaccines_given", "next_visit_date"],
}


class Extraction(BaseModel):
    visit_type: VisitType
    patient: PatientRef
    record: dict
    missing_fields: list[str] = []


class ConfirmBody(BaseModel):
    confirmed: bool = True
