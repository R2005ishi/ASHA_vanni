"""Clean up transcripts before extraction.

Prisma does well on everyday speech, but ASHAs use clinical shorthand
("IFA", "Td", "Penta") that any ASR can spell many ways. We (1) send these as
keyterms to Prisma v3.0 so recognition favours them, and (2) map common
mis-spellings / native-script spellings to one canonical form afterwards.
"""
import re

# Words we ask Prisma v3.0 to favour (sent as `keyterms`)
KEYTERMS = [
    "BP", "IFA", "Hb", "Td", "calcium", "BCG", "OPV", "Penta", "Pentavalent",
    "Rota", "PCV", "IPV", "MR", "Vitamin A", "DPT", "Hepatitis B",
    "ANC", "HBNC", "ASHA", "ANM", "kg",
]

# canonical vaccine names used everywhere in the app
VACCINES = ["BCG", "OPV0", "OPV1", "OPV2", "OPV3", "HepB0", "Penta1", "Penta2", "Penta3",
            "Rota1", "Rota2", "Rota3", "PCV1", "PCV2", "PCV-booster", "fIPV1", "fIPV2",
            "MR1", "MR2", "VitA", "DPT-booster1"]

# variant -> canonical. Matching is case-insensitive on word boundaries.
SUBSTITUTIONS = {
    # Iron Folic Acid
    "ஐ எஃப் ஏ": "IFA", "ஐஎஃப்ஏ": "IFA", "आई एफ ए": "IFA", "आईएफए": "IFA",
    "i f a": "IFA", "ifa": "IFA", "iron tablet": "IFA tablet", "iron tablets": "IFA tablets",
    "இரும்புச்சத்து மாத்திரை": "IFA மாத்திரை", "आयरन की गोली": "IFA गोली", "आयरन": "IFA",
    # Blood pressure
    "பி பி": "BP", "பிபி": "BP", "बी पी": "BP", "बीपी": "BP", "b p": "BP",
    # Haemoglobin
    "எச் பி": "Hb", "हीमोग्लोबिन": "Hb", "ஹீமோகுளோபின்": "Hb", "hemoglobin": "Hb", "haemoglobin": "Hb",
    # Tetanus-diphtheria
    "டி டி": "Td", "टी डी": "Td", "tt": "Td", "t t": "Td",
    # vaccines
    "பென்டா": "Penta", "पेंटा": "Penta", "penta": "Penta",
    "பி சி ஜி": "BCG", "बीसीजी": "BCG", "बी सी जी": "BCG",
    "ரோட்டா": "Rota", "रोटा": "Rota",
    "போலியோ": "OPV", "पोलियो": "OPV", "polio drops": "OPV",
    "மீசில்ஸ்": "MR", "खसरा": "MR",
    # units
    "கிலோ": "kg", "किलो": "kg", "kilo": "kg",
}

_PATTERNS = sorted(SUBSTITUTIONS.items(), key=lambda kv: -len(kv[0]))


def normalise(text: str) -> str:
    out = text
    for variant, canon in _PATTERNS:
        # \b does not work well for Indic scripts, so match on whitespace/punct boundaries
        pattern = r"(?<![\w])" + re.escape(variant) + r"(?![\w])"
        out = re.sub(pattern, canon, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def canon_vaccine(raw: str) -> str | None:
    """Map a free-text vaccine mention to a canonical name, e.g. 'penta 2' -> 'Penta2'."""
    s = raw.lower().replace(" ", "").replace("-", "")
    table = {
        "bcg": "BCG", "opv0": "OPV0", "opvzero": "OPV0", "opv1": "OPV1", "opv2": "OPV2", "opv3": "OPV3",
        "hepb0": "HepB0", "hepatitisb": "HepB0", "hepb": "HepB0",
        "penta1": "Penta1", "penta2": "Penta2", "penta3": "Penta3",
        "pentavalent1": "Penta1", "pentavalent2": "Penta2", "pentavalent3": "Penta3",
        "rota1": "Rota1", "rota2": "Rota2", "rota3": "Rota3",
        "pcv1": "PCV1", "pcv2": "PCV2", "pcvbooster": "PCV-booster",
        "ipv1": "fIPV1", "fipv1": "fIPV1", "ipv2": "fIPV2", "fipv2": "fIPV2",
        "mr1": "MR1", "mr2": "MR2", "measles1": "MR1", "measles2": "MR2",
        "vitamina": "VitA", "vita": "VitA", "dptbooster": "DPT-booster1", "dptbooster1": "DPT-booster1",
    }
    return table.get(s)
