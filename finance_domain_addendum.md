# Finance Market Operations Technology Addendum

Use this addendum if you only want to patch existing instructions without replacing the full files.

## Domain Context: Finance Market Operations Technology

The underlying documents for this project are expected to come primarily from Finance / Markets / Operations Technology contexts.

Examples may include:

- market operations reports
- trade lifecycle documents
- futures/options bulletins
- settlement or delivery reports
- reconciliations
- exception reports
- margin/collateral reports
- position/open-interest reports
- regulatory or control documents
- operational risk and exception documents
- payment, settlement, clearing, and confirmation documents

This domain context should help the system propose more useful extraction dictionaries and candidate-selection hints.

However, the core pipeline must remain generic. Do not hard-code logic specifically for CME, metals, options, futures, trade settlement, clearing, or any single financial document type.

Implement the system with:

1. Generic core models and services.
2. Optional domain-aware dictionary hints.
3. Configurable dictionary templates.
4. Source-grounded extraction.
5. Raw-value preservation when numeric/financial normalization is uncertain.

Finance Market Ops documents often contain dense tables, repeated headers and footers, product or contract sections, dates and effective periods, identifiers such as trade id, product code, contract code, account, desk, book, legal entity, or counterparty, numeric fields such as quantity, price, rate, notional, margin, settlement amount, open interest, volume, delta, exposure, variance, or P&L, status indicators such as NEW, UNCH, amended, cancelled, failed, pending, settled, matched, unmatched, exception, or rejected, and disclaimers, control notes, and operational caveats.

Phase 1 should not try to perfectly normalize every financial value. It should preserve raw values, source page/chunk references, and warnings. Normalized values should only be added when unambiguous.

Dictionary proposal should be domain-aware but not domain-locked. For Finance Market Ops documents, the proposed dictionary may include generic categories such as document metadata, report date or business date, product or business section, entity identifiers, key table metrics, operational status, exception or risk indicators, totals and summary values, disclaimers or caveats, and source table references. These categories should be configurable and replaceable in later phases.

Important implementation nuance: this is a generic large-PDF extraction framework, but the first target document family is Finance Market Operations Technology. Use that context to improve proposed dictionaries and sample outputs, but keep all core code document-type agnostic. Any finance-specific behavior should live in configurable hints, dictionary templates, or examples — not inside the parser, chunker, extractor, renderer, or core Pydantic models.
