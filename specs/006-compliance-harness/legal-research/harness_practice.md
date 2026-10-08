# Lightweight, automatable compliance harness for a small open-source ML model repository (state 2026-10-08)

Scope note: about 20 search/fetch calls. Where a tool or paper is cited by its canonical primary URL but the page was not fetched in this session, it is marked "(not fetched)". Maturity statements for those tools are listed under Gaps rather than asserted.

## 1. Provenance and documentation standards: what each provides, which are worth adopting

### Takeaway
For one maintainer, adopt (a) Hugging Face card YAML metadata as the published surface, (b) an internal per-dataset record whose fields are a superset of Datasheets/Data Cards and map 1:1 to SPDX 3.0 Dataset-profile fields, and (c) REUSE for repo-file licensing. Produce SPDX 3.0 or CycloneDX ML-BOM as a generated export, not as the source of truth. Croissant/Croissant-RAI is worth it only for datasets you publish yourself. OpenChain (ISO/IEC 5230 / 18974) works as a yes/no self-check list, not as something to certify.

### Cited Findings
- Datasheets for Datasets (Gebru et al.) is a question catalogue covering motivation, composition, collection process, preprocessing, uses, distribution and maintenance — [arXiv 1803.09010](https://arxiv.org/abs/1803.09010) (not fetched).
- Model Cards (Mitchell et al.) define sections: model details, intended use, factors, metrics, evaluation data, training data, ethical considerations, caveats — [arXiv 1810.03993](https://arxiv.org/abs/1810.03993) (not fetched).
- HF model cards are Markdown with a YAML header holding fields such as `language`, `license`, `datasets`, `base_model`, `tags`, `library_name`, `pipeline_tag`. For custom licenses you set `license: other` plus `license_name` and `license_link`, and `license_link` may point to a LICENSE file in the repo. Listing `datasets` makes the page show "Datasets used to train" with links — [HF Hub docs: Model Cards](https://huggingface.co/docs/hub/en/model-cards).
- Data Provenance Initiative (Longpre et al., 2023): legal and ML experts from 13 institutions audited and traced more than 1,800 text datasets. They found widespread license omissions and mislabelling on major platforms and released the Data Provenance Explorer for tracing and filtering lineage and license conditions — [arXiv 2310.16787](https://arxiv.org/abs/2310.16787); [MIT Media Lab](https://www-prod.media.mit.edu/publications/a-large-scale-audit-of-dataset-licensing-and-attribution-in-ai/).
- SPDX 3.0 AI and Dataset profiles have 36 fields in total. Optional DatasetPackage fields: `anonymizationMethodUsed`, `confidentialityLevel`, `dataCollectionProcess`, `dataPreprocessing`, `datasetAvailability`, `datasetNoise`, `datasetSize`, `datasetUpdateMechanism`, `hasSensitivePersonalInformation`, `intendedUse`, `knownBias`, `sensor`. Mandatory AIPackage items: `datasetType`, `releaseTime`, `suppliedBy`, plus `hasConcludedLicense` / `hasDeclaredLicense` relationships. An AI-BOM also draws on the Core and Software profiles — [arXiv 2504.16743 (Implementing AI-BOM with SPDX 3.0)](https://arxiv.org/pdf/2504.16743); [LF Research SPDX AI-BOM report](https://www.linuxfoundation.org/hubfs/LF%20Research/lfr_spdx_aibom_102524a.pdf).
- CycloneDX ML-BOM represents datasets, models and configurations, and records provenance and ethical considerations for datasets. Details are in the "Authoritative Guide to AI/ML-BOM" — [cyclonedx.org ML-BOM](https://cyclonedx.org/capabilities/mlbom/). (The page does not state the spec version; modelCard has been in the spec since CycloneDX 1.5 per my prior knowledge, not verified here.)
- Croissant-RAI extends Croissant (schema.org-based) with properties for the data life cycle, labelling, participatory data, safety and fairness evaluation, explainability and compliance. It builds on Data Cards and Datasheets — [arXiv 2407.16883](https://arxiv.org/pdf/2407.16883); Croissant base format: [arXiv 2403.19546](https://arxiv.org/pdf/2403.19546); [Google Research blog](https://research.google/blog/croissant-a-metadata-format-for-ml-ready-datasets/).
- REUSE: licensing information goes in per-file `SPDX-License-Identifier` / `SPDX-FileCopyrightText` headers, in `.license` sidecars, or in a `REUSE.toml` (version 1 schema; can sit in any directory and covers that directory and below; meant for large directories where headers are impractical). `reuse lint` checks the whole project, and the tool supports REUSE spec 3.3 — [REUSE spec 3.3](https://reuse.software/spec-3.3/); [reuse lint docs](https://reuse.readthedocs.io/en/stable/man/reuse-lint.html); [PyPI reuse](https://pypi.org/project/reuse/).
- OpenChain: ISO/IEC 5230 covers open source license compliance and ISO/IEC 18974 covers open source security assurance (known CVEs, dependency alerts). Self-certification means answering "yes" to every question in a checklist. 5230 has four sections: program foundation; relevant tasks defined and supported; open source content review and approval; compliance artifact creation and delivery. Both are described as suitable for organisations of any size — [OpenChain self-certification](https://openchainproject.org/checklist-iso-5230-2020); [18974 checklist](https://openchainproject.org/checklist-iso-dis-18974).

### Inferences
- The repo already has YAML dataset declarations (license, permitted use, redistribution, retention). Add SPDX-Dataset-aligned keys (`dataCollectionProcess`, `dataPreprocessing`, `anonymizationMethodUsed`, `hasSensitivePersonalInformation`, `knownBias`, `intendedUse`, `datasetSize`, `datasetAvailability`). An SPDX 3.0 / CycloneDX export then becomes a mechanical transform instead of a second register.
- Pick one BOM format. SPDX 3.0 has the richer dataset vocabulary. CycloneDX has the more mature tooling for Python and binaries (see section 3). A pragmatic option is CycloneDX for software and firmware SBOMs, with dataset/model provenance kept in the internal YAML and rendered into the HF card.
- The Data Provenance Initiative found that platform license labels are often wrong. The release gate should therefore require a primary license URL (the original publisher) as well as any HF/Zenodo label, and record any mismatch.
- REUSE.toml fits well: annotating generated firmware/C code and model-card directories by glob is cheap, and `reuse lint` is a single CI step.

### Gaps
- I could not confirm the exact CycloneDX spec version for ML-BOM or list current ML-BOM-specific generators.
- I did not fetch Google's Data Cards Playbook. Its field set was not verified here.
- Croissant-RAI property names (e.g. `rai:dataCollection`, `rai:personalSensitiveInformation`) were not verified in this session.
- I did not check whether the Data Provenance Explorer license taxonomy is published as a reusable machine-readable list.

## 2. AI Act-oriented documentation (EU training-data summary template; GPAI Code of Practice; ISO/IEC 42001)

### Takeaway
The AI Office template (published 2025-07-24) has three parts: general information, list of data sources, and data processing aspects. Every part can be filled from a well-kept per-dataset register. Open-source GPAI providers are not exempt from the training-data summary (Art. 53(1)(d)). They are exempt from the Art. 53(1)(a)/(b) technical documentation (Model Documentation Form) unless the model carries systemic risk. Whether the zoo's small models count as "GPAI" at all is a separate legal question, outside this note.

### Cited Findings
- The template was published 2025-07-24 under Art. 53(1)(d). The summary obligation applies to all GPAI models, including open-source ones — [Securiti](https://securiti.ai/eu-publishes-template-for-public-summaries-of-ai-training-content/); [WilmerHale](http://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/european-commission-releases-mandatory-template-for-public-disclosure-of-ai-training-data).
- Template structure per WilmerHale:
  1. General information: provider and model identification with versions and dates; modalities; estimated training data size; language and demographic coverage.
  2. List of data sources: large datasets named individually, small ones may be aggregated; commercially licensed data; web-scraped data with a domain list (top 10% of domains; SMEs: top 5% or 1,000 domains); user data (social media, email, model interactions); synthetic data, including which models generated it; other.
  3. Data processing aspects: measures to respect TDM opt-outs (copyright) and measures to remove illegal content.
  Dates: effective 2025-08-02; models placed on the market before then must comply by 2027-08-02; AI Office enforcement from 2026-08-02; updates every six months or on material change. Anyone who significantly modifies an existing model reports only the training content of the modification — [WilmerHale](http://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/european-commission-releases-mandatory-template-for-public-disclosure-of-ai-training-data). (Secondary law-firm source. Field names are paraphrased, not the official wording.)
- GPAI Code of Practice, Transparency chapter: three Measures for Art. 53(1)(a)/(b) and Annexes XI/XII, plus a Model Documentation Form. The form includes provider legal name, model name, public versions, model authenticity/provenance evidence, release date, licensing, technical specs, use cases, datasets, and compute/energy. Information for the AI Office is supplied only on request. Previous versions must be kept for 10 years after market placement. Art. 53(2) exempts free/open-source models unless they have systemic risk — [artificialintelligenceact.eu CoP Transparency](https://artificialintelligenceact.eu/en/cop-transparency); [overview](https://artificialintelligenceact.eu/code-of-practice/).

### Inferences
- Training on frontier-LLM teacher outputs is "synthetic data" in template terms, so the register must record the teacher model names and versions per dataset or topic. The repo already tracks teachers, which fits.
- Web-scraped redacted texts need per-domain counts in the register, so the "top N% domains" list can be generated automatically. Store the domain and byte/token count per document in the out-of-git manifest.
- "Measures to respect TDM opt-outs" need evidence: log the robots.txt/TDMRep decision per URL at crawl time (section 3). The summary can then cite a mechanism plus counts.
- A 10-year retention of versioned model documentation is cheap if each release tag freezes the generated card, register snapshot and BOM as release assets.
- ISO/IEC 42001: nothing was fetched. Treat it as orientation only (Annex A controls on data for AI systems: data acquisition, quality, provenance, preparation). See Gaps.

### Gaps
- I did not fetch the official template PDF from digital-strategy.ec.europa.eu. Exact field labels and the SME definition should be checked against the original.
- The Model Documentation Form fields on training data (data type, provenance, curation, detection of unsuitable sources, bias) were not readable: the page shows the form as images.
- ISO/IEC 42001 Annex A control numbering for data provenance was not verified (the standard is paywalled; no free primary source found).
- Whether small task-specific models (tinyML, distilled SLMs) meet the AI Act GPAI definition was not researched.

## 3. Automated checks used in practice

### Takeaway
A CI-runnable set for one maintainer:
- License: `reuse lint`, a Python dependency license check, and HF Hub / Zenodo API metadata fetch compared with the declared license.
- Secrets: gitleaks (already in place).
- PII: Presidio with German recognisers plus WIMBD-style high-precision regex on every text artefact that enters training or publication.
- SBOM: cyclonedx-py for the Python environment, syft for firmware/build directories.
- Memorisation: canary strings plus n-gram overlap between model outputs and the scraped corpus.
- Crawl-time opt-out: robots.txt via an RFC 9309-conformant parser, plus TDMRep (`/.well-known/tdmrep.json`, header, meta) and ai.txt, with the decision logged per URL.

### Cited Findings
- Presidio now lives under a community org: docs moved from microsoft.github.io to presidio.dataprivacystack.org, and the site says "Presidio is transitioning to a community-owned project" — [Presidio docs](https://presidio.dataprivacystack.org/).
- Presidio covers global entities (credit card, crypto, email, IP, phone, etc.) and country-specific recognisers for 17+ countries. The docs list 11 German-specific recognisers, including tax ID, passport, health insurance ID, vehicle registration plate and commercial register number. Phone detection can be scoped to regions via `supported_regions` — [Presidio supported entities](https://presidio.dataprivacystack.org/supported_entities/).
- WIMBD (AllenAI) uses three high-precision regexes for emails, phone numbers and IPs, with post-processing to cut false positives: emails must have a "." in the domain; phone matches are dropped near ISBN/DOI/"#" context — [arXiv 2310.20707](https://arxiv.org/pdf/2310.20707).
- FineWeb is built on the open-source datatrove library (URL blocklists, trafilatura extraction, quality filters, MinHash dedup, PII anonymisation). FineWeb-2 anonymises emails and IP addresses — [fineweb-2 repo](https://github.com/huggingface/fineweb-2). The FineWeb dataset is ODC-By — [HF dataset page](https://huggingface.co/datasets/HuggingFaceFW/fineweb). The fetched page excerpt did not show its robots.txt/opt-out section, so that is unverified here.
- TDMRep declares a TDM reservation through an HTTP header, an HTML `<meta>` or `/.well-known/tdmrep.json`. ai.txt sets AI-training permission per file type and defaults to opted out, the opposite of TDMRep — [ScrapingBee on TDMRep/ai.txt](https://www.scrapingbee.com/blog/tdmrep-ai-txt-scraping-controls/) (secondary).
- Spawning's `datadiligence` (MIT) checks opt-outs through the Spawning API, X-Robots-Tag headers and C2PA metadata. Its README does not mention robots.txt or TDMRep. It is small (about 41 stars, 26 commits), and bulk use needs a Spawning API key — [GitHub Spawning-Inc/datadiligence](https://github.com/Spawning-Inc/datadiligence).
- The community list ai.robots.txt maintains AI crawler user-agents — [github.com/ai-robots-txt/ai.robots.txt](https://gittrend.io/repo/ai-robots-txt/ai.robots.txt) (aggregator page).
- Training-data extraction and memorisation: the "Secret Sharer" canary method inserts random canary sequences and measures exposure — [Carlini et al., arXiv 1802.08232](https://arxiv.org/abs/1802.08232) (not fetched). Follow-up work studies personal-information parroting in LMs — [arXiv 2602.20580](https://arxiv.org/pdf/2602.20580) (found in search; content not read).
- Tools named in the brief, referenced by canonical repos only (not fetched; maturity not verified): scancode-toolkit (https://github.com/aboutcode-org/scancode-toolkit), licensee (https://github.com/licensee/licensee), pip-licenses (https://github.com/raimon49/pip-licenses), licensecheck (https://github.com/FHPythonUtils/LicenseCheck), cyclonedx-python (https://github.com/CycloneDX/cyclonedx-python), syft (https://github.com/anchore/syft), trufflehog (https://github.com/trufflesecurity/trufflehog), gitleaks (https://github.com/gitleaks/gitleaks), scrubadub (https://github.com/LeapBeyond/scrubadub).

### Inferences
- Do not rely on datadiligence for robots.txt/TDMRep. A small in-repo checker is easier to own: Python `urllib.robotparser` or an RFC 9309 parser, plus a fetch of `/.well-known/tdmrep.json` and the `tdm-reservation` header/meta, plus `/ai.txt`. It writes `{url, fetched_at, robots_allowed, tdm_reserved, ai_txt}` into the crawl manifest. The release gate then fails if any training document lacks a manifest entry or has `tdm_reserved=1` without a recorded licence.
- PII gate: run Presidio (de + en, with German recognisers) plus WIMBD-style regex over redacted texts before training, and over model outputs and eval results before publication. Fail on high-confidence hits outside an allowlist (e.g. public company addresses). The project moving away from Microsoft is a maintenance risk to watch; pin versions.
- Memorisation gate (cheap version): (1) insert a few unique canary strings into the redacted training set and check that the released model does not complete them from their prefixes; (2) generate N samples per topic and compute the longest n-gram overlap against the scraped corpus (e.g. a 50-token or 13-gram threshold, a common choice in contamination checks). Block release over the threshold.
- Dataset license via APIs: the HF Hub `cardData.license` (via `huggingface_hub`) and Zenodo record `metadata.license` can be compared with the YAML-declared license. Mismatch means fail or manual waiver, which matters given the DPI finding that platform labels are often wrong.
- Firmware SBOM: firmware/C code generated from the repo has no package manager. A hand-written CycloneDX component list (e.g. vendored HALs, CMSIS) validated by the CycloneDX schema may beat syft directory scanning. Not verified.

### Gaps
- I did not verify the maintenance status or latest releases of scancode, licensee, pip-licenses vs licensecheck, scrubadub (believed stale, not verified), syft or cyclonedx-py.
- No maintained, widely used Python library for TDMRep or ai.txt was found in this session.
- FineWeb's exact robots.txt handling (Common Crawl's crawler obeys robots.txt at crawl time; FineWeb-specific opt-out handling) was not confirmed from a primary page.
- No primary source was fetched for standard n-gram thresholds for extraction tests.

## 4. Compliance registers (record of processing per dataset/model; cadence; tie to release gates)

### Takeaway
Keep one machine-readable register entry per dataset and per model release. It covers the GDPR Art. 30 RoPA core (purpose, categories of data and subjects, recipients, retention, safeguards), the licensing/permitted-use/redistribution fields, the opt-out and PII evidence, and owner/review date. The release gate fails on missing fields, a stale review date, or a failed check.

### Cited Findings
- AI Office template data-source categories (public datasets, licensed, web-scraped with domain lists, user data, synthetic, other) and processing measures (TDM opt-out, illegal content) — [WilmerHale](http://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/european-commission-releases-mandatory-template-for-public-disclosure-of-ai-training-data).
- Summary updates every six months or on material change — same source.
- 10-year retention of model documentation versions under the CoP — [CoP Transparency](https://artificialintelligenceact.eu/en/cop-transparency).
- SPDX Dataset profile fields usable as register keys (anonymizationMethodUsed, hasSensitivePersonalInformation, confidentialityLevel, datasetUpdateMechanism, etc.) — [arXiv 2504.16743](https://arxiv.org/pdf/2504.16743).
- BigCode practice: opt-out requests come in as GitHub issues generated from the "Am I in The Stack" tool, scoped to repos, commits or issues — [Turing Way BigCode case study](https://book.the-turing-way.org/project-design/data-governance/bigcode_casestudy); [BigCode The Stack](https://www.bigcode-project.org/docs/about/the-stack/).

### Inferences
- Suggested per-dataset register fields:
  - id, topic, source_url, primary_license_url, spdx_license, license_verified_at, permitted_use, redistribution, attribution_text
  - collection_method (scrape / download / teacher-generated), teacher_models[], tdm_check_summary
  - personal_data (y/n, categories), legal_basis (GDPR Art. 6, e.g. legitimate interest with balancing-test reference), anonymization_method, pii_scan {tool, version, date, hits}
  - storage_location (outside git), retention_until, deletion_procedure
  - known_bias, intended_use
  - owner, last_reviewed, next_review
- Per model release: base_model + license, datasets[], teachers[] + their terms-of-use references, eval results, memorisation check result, SBOM path, card hash, release tag.
- Cadence: review on each release and at least every six months, matching the AI Office update rhythm. The gate fails if `next_review < today`.
- Gate wiring: a JSON Schema / pydantic validation of the register, then one check per field class (license allowlist, URL reachability optional/non-blocking, PII report present and clean, crawl manifest coverage 100%, retention not expired). Waivers go in a signed-off `waivers.yaml` with an expiry date.
- An opt-out/takedown channel like BigCode's (a GitHub issue template plus removal from the next release) is cheap and transferable.

### Gaps
- I did not fetch a primary source (EDPB/BfDI template) for the Art. 30 RoPA field list; the fields above come from the regulation's standard content and are not cited here.

## 5. Attribution generation (NOTICE / THIRD_PARTY / card sections from structured metadata)

### Takeaway
Generate attribution from the same register: render a THIRD_PARTY_NOTICES.md (datasets, base model, teacher terms, code dependencies) and the HF card "Training data / Attribution" section with a template (e.g. Jinja2). Use `reuse` for repo files and the SBOM tool for dependency licences.

### Cited Findings
- HF card YAML `datasets` and `base_model` fields produce linked "Datasets used to train" / base-model references on the Hub. Custom licenses use `license: other` + `license_name` + `license_link` — [HF model cards docs](https://huggingface.co/docs/hub/en/model-cards).
- REUSE tracks per-file copyright and licence (headers, `.license` files, REUSE.toml). `reuse` can also emit an SPDX document of the repo (per my prior knowledge, `reuse spdx`; not verified this session) — [REUSE spec 3.3](https://reuse.software/spec-3.3/).
- ODC-By datasets such as FineWeb require attribution — [FineWeb dataset card](https://huggingface.co/datasets/HuggingFaceFW/fineweb).

### Inferences
- Pattern: register YAML → Jinja2 → (a) `THIRD_PARTY_NOTICES.md` in the repo and each HF upload, (b) the model-card attribution section, (c) the CycloneDX/SPDX export. The gate checks that the rendered files are byte-identical to the committed ones (a "no drift" check) and that every dataset with `redistribution: attribution-required` has a non-empty `attribution_text`.
- Python dependency notices: pip-licenses can print license texts (`--with-license-file`, believed; not verified) for the frozen environment.

### Gaps
- No dedicated, maintained "NOTICE generator from dataset metadata" tool was found. Custom templating seems standard; not verified with a survey.

## 6. Open-source ML projects with strong compliance tooling: what transfers

### Takeaway
Transferable practices: BigCode's self-service opt-out plus a governance card; DPI's practice of re-verifying licences at the source; AllenAI's WIMBD-style corpus scans (PII regex, counts); FineWeb/datatrove's PII anonymisation step built into the pipeline.

### Cited Findings
- BigCode: "Am I in The Stack" lets developers check inclusion and file an opt-out as a generated GitHub issue (all repos or selected repos, commits, issues). Turing Institute community research in early 2023 found that people want to know about inclusion and have a choice, which led to a governance card — [Turing Way case study](https://book.the-turing-way.org/project-design/data-governance/bigcode_casestudy); [OECD.AI](https://oecd.ai/en/wonk/bigcode); [ServiceNow](https://www.servicenow.com/blogs/2024/bigcode-open-innovation-case-study).
- AllenAI WIMBD: corpus analysis including PII regex counts across pretraining corpora — [arXiv 2310.20707](https://arxiv.org/pdf/2310.20707).
- HF FineWeb / FineWeb-2: datatrove pipeline with PII anonymisation (emails, IPs) and ODC-By licence — [fineweb-2](https://github.com/huggingface/fineweb-2); [FineWeb](https://huggingface.co/datasets/HuggingFaceFW/fineweb).
- Data Provenance Initiative: audits show licence labels on aggregators are unreliable — [arXiv 2310.16787](https://arxiv.org/abs/2310.16787).

### Inferences
- For the zoo: (1) a "governance" section in the HF org card and in each model card linking an opt-out issue template; (2) a WIMBD-like scan report (PII counts before and after redaction, domain distribution) attached to each release as an artefact, which also feeds the AI Office "top domains" list; (3) a datatrove-style redaction step that is versioned and recorded in the register.

### Gaps
- BigScience/BLOOM data governance (ROOTS data governance, Responsible AI License), EleutherAI (The Pile datasheet), Dolma (AllenAI ImpACT licence, opt-out form) and Common Corpus/Pleias (fully open-licence corpus) were not fetched in this session. Their specific mechanisms should be verified before citing.
