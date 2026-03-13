# Architecture Overview

## Core decision

The canonical source for generated documents is a versioned DOCX template rendered by `docxtemplater`.

Pipeline:

1. User creates or edits a document in the Mini App.
2. API stores normalized payload plus `template_key` and `template_version`.
3. API requests DOCX rendering from `apps/docgen`.
4. `docgen` renders a DOCX from the chosen template and payload.
5. API sends the DOCX to Gotenberg to convert it into PDF.
6. API stores both files in S3-compatible storage and saves immutable document metadata.

## Why DOCX-first

- It matches the product requirement: system templates are preloaded Word files with placeholders.
- It avoids duplicating layout logic in HTML and DOCX.
- It supports later delivery as both DOCX and PDF from the same template source.

## Service boundaries

- `miniapp`: UI, Telegram bridge, local state, API calls.
- `api`: auth, users, contacts, counterparties, catalog, documents, storage, Telegram bot hooks.
- `docgen`: dedicated DOCX rendering service because `docxtemplater` is a Node ecosystem tool.

## Document model additions

For stable regeneration and auditability, the `documents` entity should keep:

- `template_key`
- `template_version`
- `render_payload_json`
- `source_docx_file_url`

`html_snapshot` should remain optional and non-authoritative.

## Telegram notes

- Validate `initData` on the backend.
- Keep bot logic in the API service for MVP; split it only if the bot grows beyond launch and file-delivery use cases.
- Do not depend on a single share mechanism. Keep Telegram and file-download fallbacks.
