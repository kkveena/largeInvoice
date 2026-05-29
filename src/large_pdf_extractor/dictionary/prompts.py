"""Prompts and configurable dictionary templates.

The category templates below are the home of *domain-aware but document-type
agnostic* hints. They are Finance-Market-Ops friendly (dates, identifiers,
metrics, statuses, disclaimers) yet contain no CME/metals/options-specific
parsing logic. They are fully replaceable: pass a different template list to
``DictionaryService`` and the rest of the pipeline is unchanged.
"""

from __future__ import annotations

from typing import Any

DICTIONARY_SYSTEM_PROMPT = (
    "You are an extraction-dictionary designer for large documents. "
    "Your ONLY job is to propose a dictionary describing WHAT to extract and "
    "WHERE/HOW to find it. Do NOT extract or return any actual values. "
    "Return strict JSON matching the requested schema. Keep the dictionary "
    "generic and document-type agnostic; use the document signals only to "
    "tune sections, examples, and candidate-selection hints."
)

DICTIONARY_USER_INSTRUCTIONS = (
    "Propose an extraction dictionary as strict JSON with keys: dictionary_id, "
    "document_id, name, description, generated_from_strategy, items. Each item "
    "must include: item_id, document_section, entity_name, description, "
    "instruction_prompt, expected_type (one of string|number|date|boolean|list|"
    "table|object), required, examples, normalization_hint, "
    "candidate_selection_hints. Do not include any extracted values."
)


# Configurable, replaceable default categories. Generic + finance-ops aware.
DEFAULT_CATEGORY_TEMPLATES: list[dict[str, Any]] = [
    {
        "item_id": "document_title",
        "document_section": "document metadata",
        "entity_name": "document_title",
        "description": "The overall title or heading of the document.",
        "instruction_prompt": "Extract the document title or main heading.",
        "expected_type": "string",
        "required": True,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": ["title", "bulletin", "report", "products"],
    },
    {
        "item_id": "report_or_business_date",
        "document_section": "document metadata",
        "entity_name": "report_or_business_date",
        "description": "Primary report date or business date of the document.",
        "instruction_prompt": "Extract the report date or business date. Preserve the raw date text.",
        "expected_type": "date",
        "required": True,
        "examples": [],
        "normalization_hint": "ISO 8601 (YYYY-MM-DD) only if unambiguous.",
        "candidate_selection_hints": ["date", "business date", "report date", "as of"],
    },
    {
        "item_id": "product_or_business_section",
        "document_section": "product or business section",
        "entity_name": "product_or_business_section",
        "description": "Primary product, contract, or business section the document covers.",
        "instruction_prompt": "Identify the main product or business section title.",
        "expected_type": "string",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": ["product", "contract", "section", "group"],
    },
    {
        "item_id": "entity_identifiers",
        "document_section": "entity identifiers",
        "entity_name": "entity_identifiers",
        "description": "Key identifiers such as product code, contract code, account, desk, book, legal entity, or counterparty.",
        "instruction_prompt": "List any entity identifiers present. Preserve raw codes.",
        "expected_type": "list",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": [
            "code",
            "id",
            "account",
            "desk",
            "book",
            "entity",
            "counterparty",
            "symbol",
        ],
    },
    {
        "item_id": "key_table_metrics",
        "document_section": "key table metrics",
        "entity_name": "key_table_metrics",
        "description": "Important numeric metrics from tables (e.g. quantity, price, rate, volume, open interest, settlement).",
        "instruction_prompt": "Extract representative numeric metrics from tables. Preserve raw values.",
        "expected_type": "table",
        "required": False,
        "examples": [],
        "normalization_hint": "Do not strip units or symbols unless unambiguous.",
        "candidate_selection_hints": [
            "volume",
            "open interest",
            "price",
            "rate",
            "quantity",
            "settlement",
            "delta",
        ],
    },
    {
        "item_id": "operational_status",
        "document_section": "operational status",
        "entity_name": "operational_status",
        "description": "Operational status indicators (e.g. NEW, UNCH, amended, cancelled, settled, matched, exception).",
        "instruction_prompt": "Extract any operational status indicators present.",
        "expected_type": "list",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": [
            "status",
            "new",
            "unch",
            "amended",
            "cancelled",
            "settled",
            "matched",
            "exception",
            "final",
        ],
    },
    {
        "item_id": "exception_or_risk_indicators",
        "document_section": "exception or risk indicators",
        "entity_name": "exception_or_risk_indicators",
        "description": "Exception, failure, or operational-risk indicators.",
        "instruction_prompt": "Extract exception or risk indicators if present.",
        "expected_type": "list",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": [
            "exception",
            "failed",
            "rejected",
            "unmatched",
            "pending",
            "out-of-floor",
            "error",
        ],
    },
    {
        "item_id": "totals_and_summary_values",
        "document_section": "totals and summary values",
        "entity_name": "totals_and_summary_values",
        "description": "Totals, subtotals, or summary aggregate values.",
        "instruction_prompt": "Extract any totals or summary aggregate values. Preserve raw values.",
        "expected_type": "number",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": ["total", "subtotal", "sum", "aggregate", "grand total"],
    },
    {
        "item_id": "disclaimers_or_caveats",
        "document_section": "disclaimers or caveats",
        "entity_name": "disclaimers_or_caveats",
        "description": "Legal disclaimers, control notes, or data-quality caveats.",
        "instruction_prompt": "Extract any disclaimer, control note, or caveat text.",
        "expected_type": "string",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": [
            "disclaimer",
            "caveat",
            "subject to",
            "no warranty",
            "control",
            "provisional",
        ],
    },
    {
        "item_id": "source_table_references",
        "document_section": "source table references",
        "entity_name": "source_table_references",
        "description": "References to source tables, pages, or schedules.",
        "instruction_prompt": "Extract references to source tables, schedules, or page sections.",
        "expected_type": "list",
        "required": False,
        "examples": [],
        "normalization_hint": None,
        "candidate_selection_hints": ["table", "schedule", "page", "appendix", "exhibit"],
    },
]
