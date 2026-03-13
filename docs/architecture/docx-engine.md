# DOCX Engine Notes

## Docxtemplater usage

Use `docxtemplater` as the primary template engine for built-in invoice and proposal templates.

Free or core-friendly capabilities:

- text placeholders
- loops for rows and repeated blocks
- conditionals
- simple table population when loops are placed inside Word tables

Capabilities that usually require extra modules or stricter review:

- advanced image replacement
- complex table generation
- HTML embedding
- chart-like content

## Alternatives worth tracking

- `docx-templates`: open-source JavaScript templating library for DOCX with commands inside templates.
- `easy-template-x`: open-source TypeScript library with a simpler token model.

Current recommendation:

- keep `docxtemplater` as the main engine because it matches the placeholder-based template approach
- evaluate alternatives only for cost or licensing pressure, not for MVP architecture

## Template packaging

Each built-in template should contain:

- `template.docx`
- `manifest.json`
- `schema.json`
- `preview.png` or later preview asset

This allows the API and Mini App to know what data a template expects without inspecting DOCX internals at runtime.
