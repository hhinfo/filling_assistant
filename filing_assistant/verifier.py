from __future__ import annotations
from typing import Dict, Tuple
import os
from .schema import CONTROLLED_VOCAB, normalize

USE_MOCK = os.environ.get("FA_MOCK_OPENAI", "false").lower() == "true"

def mock_verify_label(raw_header: str) -> Tuple[str, float, str]:
    n = normalize(raw_header)
    for label, variants in CONTROLLED_VOCAB.items():
        if n == label.replace("_", " "):
            return label, 0.95, "mock-exact"
        for v in variants:
            if n == normalize(v):
                return label, 0.9, "mock-variant"
    for label in CONTROLLED_VOCAB.keys():
        if any(tok in n for tok in label.split("_")):
            return label, 0.6, "mock-fuzzy"
    return "unknown", 0.3, "mock-unknown"

def verify_label(raw_header: str) -> Tuple[str, float, str]:
    if USE_MOCK:
        return mock_verify_label(raw_header)
    try:
        from openai import OpenAI
        client = OpenAI()
        prompt = (
            "You are a data labeling assistant. Map the provided column header to one of the controlled "
            "vocabulary labels. If none match, answer 'unknown'.\n"
            f"Controlled vocabulary keys: {list(CONTROLLED_VOCAB.keys())}\n"
            f"Header: {raw_header}\n"
            "Answer in JSON with keys: label, confidence (0-1)."
        )
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        text = resp.output[0].content[0].text  # adjust to your SDK version if needed
        import json as _json
        parsed = _json.loads(text)
        return parsed.get("label","unknown"), float(parsed.get("confidence",0.5)), "openai"
    except Exception:
        return mock_verify_label(raw_header)
