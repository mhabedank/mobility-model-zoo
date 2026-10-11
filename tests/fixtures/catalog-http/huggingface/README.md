# Hugging Face Hub: trimmed recorded responses

Trimmed recorded responses of `GET https://huggingface.co/api/datasets?search=…&full=true`,
recorded on 2026-10-11 for `tests/catalog/test_harvest_huggingface.py`.

`datasets.json` holds six dataset records from several searches. The test serves them through a
mock that imitates the Hub search (substring of the id, `filter=language:<code>`). Card text
(`description`), file lists and free-form tags are removed; `cardData` keeps only licence,
language and pretty name. Account names that may belong to individuals are replaced by `example-user-1` and `example-user-2`; the remaining accounts are organisations (a university research group, companies, an institute).
