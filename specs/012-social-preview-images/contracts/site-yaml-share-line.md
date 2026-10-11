# Contract: `share_line` in the site schemas

Added to both `src/mobility_model_zoo/site/schemas/site.schema.json` (per model) and `site-config.schema.json` (zoo):

```json
"share_line": {
  "type": "string",
  "minLength": 1,
  "maxLength": 90,
  "description": "One line on the preview image when the page is shared: what the model does and why it matters. No numbers and no {metric:…} placeholders (an image cannot carry the note that says what a number is measured against). If absent, the tagline is used and must meet the same rules (check B6)."
}
```

The JSON schema enforces only the length. The rules on numbers, placeholders and characters are B6, because they need the F2 pattern and the font ranges.

The scout-large text gets a share line, for example:

```yaml
share_line: Finds jobs, pains and gains in mobility texts, each with a verbatim quote.
```
