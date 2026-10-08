# License, attribution and ToS obligations for the Mobility Model Zoo

Scope: one private individual in Germany publishing models (and maybe datasets) on Hugging Face and code on GitHub (Apache-2.0). Current as of 2026-10-08. Not legal advice. Confidence: H = high, M = medium, L = low.

Source note: pages marked "(fetched)" were retrieved in this session through a summarizing fetch tool. Its quotes may be lightly paraphrased, so check the exact wording against the primary page before pasting it into a NOTICE. Pages marked "(canonical text, not re-fetched)" are standard license texts cited from their official URL. Their wording is well known but was not re-checked in this session.

## Q1. CC BY 4.0 / CC BY-SA 4.0: are model weights "Adapted Material"? What does CC say? What attribution? Does ShareAlike bind weights?

### Takeaway
CC does not say whether trained weights are "Adapted Material". Its position is "it depends": the license only applies where an act needs copyright permission, which is unsettled for training and weights. CC's own advice is the conservative path. Attribute the dataset (a link is enough for training), and if the model is based on BY-SA content and shared publicly, use the same license. Plan: CC BY-SA 4.0 for the MIMII model (already planned) and full TASL attribution for every CC dataset in the model card and the NOTICE. Confidence M.

### Cited Findings
- CC (May 2025, "Using CC-licensed works for AI training"): "It depends. CC licenses apply only when copyright permission is required. If exceptions or limitations apply, then the CC license terms don't apply." (fetched) — [CC: Using CC-licensed works for AI training](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)
- Same page, on attribution: "For AI model training, attribution could be a simple link to the source of the dataset used to train the model. Where retrieval-augmented generation (RAG) or other methods are available, providing attribution to the CC-licensed work tied to the particular model output with a link to the source is ideal." — [CC AI training guide](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)
- Same page, on ShareAlike: "If AI models or outputs are based on ShareAlike content and they will be shared publicly, following the ShareAlike condition would require AI developers to use the same CC license as the original works." — [CC AI training guide](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)
- Same page, best practice: CC recommends following the license conditions "even in situations where copyright may not require it", and to assume "the most restrictive legal interpretation for those who wish to take a conservative approach and minimize risk." — [CC AI training guide](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)
- The guide does not say explicitly whether model weights are Adapted Material (checked by the fetch). — [CC AI training guide](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)
- BY-SA 4.0 §1(a) defines Adapted Material as material "derived from or based upon the Licensed Material" in which the material is "translated, altered, arranged, transformed, or otherwise modified in a manner requiring permission under the Copyright and Similar Rights held by the Licensor". The permission test is the key part. (fetched, summarized) — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
- BY-SA 4.0 §3(b): Adapted Material must be licensed under "a Creative Commons license with the same License Elements, this version or later, or a BY-SA Compatible License", i.e. CC BY-SA 4.0 or later, or a license CC lists as compatible. (fetched) — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
- §3(b) also says you may not offer or impose extra terms, or apply Effective Technological Measures to Adapted Material, that restrict the Adapter's License (canonical text, not re-fetched). — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
- §3(a)(1) attribution elements: (A)(i) identification of the creator(s) and anyone designated to receive attribution, "in any reasonable manner requested by the Licensor"; (ii) a copyright notice; (iii) a notice that refers to this Public License; (iv) a notice that refers to the disclaimer of warranties; (v) a URI or hyperlink to the Licensed Material "to the extent reasonably practicable". (B) indicate if you modified the material and keep an indication of any previous modifications. (C) indicate that the material is licensed under this Public License and include the text of, or the URI or hyperlink to, the license. §3(a)(2): you may satisfy these conditions "in any reasonable manner based on the medium, means, and context", including a URI or hyperlink to a resource that holds the information. §3(a)(3): remove the information on the licensor's request. (canonical text, not re-fetched; partly confirmed by the fetch summary "retain creator identification, copyright notices, references to the license, and disclaimer notices where reasonably practicable") — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en); [CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode.en)
- The 4.0 licenses also cover sui generis database rights under the same conditions. This matters in the EU, where training data extracted from a database can hit the database right. "Under 4.0, sui generis database rights are licensed under the same license conditions as copyright." (fetched, FAQ) — [CC FAQ](https://creativecommons.org/faq/)
- The CC FAQ says the licenses do not limit computational analysis or ML uses, but that privacy, data protection and research-ethics rules apply independently. (fetched; the fetch summary paraphrased this, so verify wording) — [CC FAQ](https://creativecommons.org/faq/)
- License rights end automatically on breach and are restored automatically if the breach is cured within 30 days of discovery (§6). (fetched) — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
- CC signals: CC presented this framework in June 2025 as machine-readable preferences for AI reuse ("yes/no" plus conditions such as credit). It is in pilot or alpha status, and the press describes it as not legally enforceable ("social and ethical markers"). — [CC: what we built together in 2025](https://creativecommons.org/2025/12/19/what-we-built-together-in-2025/); [Maginative](https://www.maginative.com/article/creative-commons-unveils-framework-to-signal-ai-use-permissions/); [eWeek](https://www.eweek.com/news/creative-commons-signals/)

### Inferences
- German or EU law: training probably falls under the TDM exceptions (§44b UrhG / Art. 4 DSM Directive; §60d UrhG for scientific research). If so, the CC conditions arguably do not apply to the training act itself. Whether published weights reproduce or "adapt" the work is unsettled. (M; other researchers cover the TDM side)
- Harness rule: treat every CC dataset as if the weights were Adapted Material. That means full TASL attribution, a modification statement ("used as training data; preprocessed/segmented/relabelled"), and the same license for any model trained on BY-SA data. Cost is low and it removes the risk. (H that this is best practice)
- CC BY data has no share-alike. A model trained only on CC BY data (ROAD, can-train-and-test, UCI HAR) can be released under Apache-2.0, but it must still carry the attribution. The license notice should say the training data is CC BY 4.0 and the weights are Apache-2.0. (H)
- BY-SA data (MIMII): the model weights go under CC BY-SA 4.0. Inference or training code shipped in the same repo can stay Apache-2.0 because it is not derived from the data. State per-file licenses (REUSE) so the weights' BY-SA license does not spill onto the code. (M-H)
- §3(b) bans extra terms and technical restrictions. So a BY-SA model must not be gated on HF with terms that restrict reuse, and must not get an "acceptable use" add-on that limits the license. (M)
- Where to attribute: (1) an HF model card section "Training data and attribution" with TASL per dataset; (2) a NOTICE or ATTRIBUTION.md file in the model repo; (3) the YAML `datasets:` field where a Hub ID exists. §3(a)(2) allows a link to a page with the information. (H)

### Gaps
- No court decision and no CC statement says outright that trained weights are or are not Adapted Material. Unsettled.
- I did not retrieve the exact 2021 CC statements (e.g. the "Should CC-licensed content be used to train AI? It depends" blog post). The 2025 guide supersedes or summarizes them.
- I could not confirm CC signals' launch status after the 2025 pilot (as of October 2026).

## Q2. Republishing third-party datasets on Hugging Face

### Takeaway
CC BY and BY-SA allow redistribution, including modified copies, if TASL attribution is kept (and the same license for BY-SA adaptations). The host terms I checked (Zenodo) do not ban re-hosting and defer to the per-record license. UCI asks for citation. Still check each record's own license field, because the license applies per record, not per host. Confidence M-H.

### Cited Findings
- Zenodo terms: "Users of content ("Users") shall respect applicable license conditions." "Download and use of content from Zenodo does not transfer any intellectual property rights in the content to the User." Metadata is CC0 "unless specified otherwise". No explicit clause on re-hosting or mirroring. CERN may restrict access that "interferes with its operations", which matters for bulk download. (fetched) — [Zenodo Terms of Use](https://about.zenodo.org/terms/)
- UCI: the general citation is "Markelle Kelly, Rachel Longjohn, Kolby Nottingham, The UCI Machine Learning Repository, https://archive.ics.uci.edu". For datasets: "To cite a particular dataset, please see the Cite button on each dataset page." The citation page has no repository-wide redistribution clause. (fetched) — [UCI citation policy](https://archive.ics.uci.edu/citation)
- CC BY-SA 4.0 §2(a)(1) grants the right to "reproduce and Share the Licensed Material, in whole or in part" and to produce, reproduce and Share Adapted Material. The grant is "worldwide, royalty-free, non-sublicensable, non-exclusive, irrevocable". (fetched) — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
- HF model and dataset metadata: `license` takes a Hub license identifier. For licenses not on the list, use `license: other` plus `license_name` and `license_link`, which may point to a LICENSE file in the repo. (fetched) — [HF model cards docs](https://huggingface.co/docs/hub/model-cards)

### Inferences
- Rules for republishing on HF: keep the original license (`license: cc-by-4.0` / `cc-by-sa-4.0`); put the original creators, the citation (BibTeX from the Zenodo record, the DTU record, or the UCI "Cite" button), the source DOI or URL and a modification statement in the dataset card; ship the original LICENSE text or a link to it; never re-license CC BY data under a different license for the dataset itself. (H)
- MIMII is BY-SA. A processed or derived dataset (features, splits) on HF must be CC BY-SA 4.0. (H)
- can-train-and-test is distributed via DTU / Bitbucket. Bitbucket's Atlassian terms govern use of the service, not the license of hosted content, so the repository's own LICENSE file decides. (M; Atlassian terms were not fetched)
- Privacy check before republishing: ROAD and can-train-and-test hold CAN traffic from real vehicles. A VIN or other identifiers could be personal data under GDPR (CC FAQ: data protection applies separately). Make this a human decision gate. (M)
- Prefer linking or pointing over re-hosting where the raw dataset is already stable on Zenodo with a DOI. Re-hosting adds duty without benefit unless the data is transformed. (M, judgment)

### Gaps
- DTU Data (figshare-based) terms and the can-train-and-test Bitbucket LICENSE file were not retrieved in this session. Verify per record.
- The current HF Terms of Service and Content Policy were not fetched. Verify the clauses on uploader warranties (that you hold the rights to upload).
- The UCI HAR dataset page license field was not fetched. The project fact says CC BY 4.0; verify on the dataset page.

## Q3. Apache-2.0, MIT, BSD obligations; NOTICE files; generated C code; REUSE

### Takeaway
Apache-2.0 §4 requires, on redistribution: give a copy of the license; mark modified files prominently; keep copyright, patent, trademark and attribution notices; and include the readable contents of any NOTICE file that came with imported code. MIT and BSD-3 require keeping the copyright notice and license text, and BSD-3 also requires that in binary distributions (firmware). Whether emlearn's generated C code carries emlearn's MIT license is not stated, so plan for MIT attribution. Confidence H for the license texts, M for emlearn output.

### Cited Findings
- Apache-2.0 §4(a) give recipients a copy of the License; §4(b) "cause any modified files to carry prominent notices stating that You changed the files"; §4(c) retain "all copyright, patent, trademark, and attribution notices from the Source form of the Work"; §4(d) if the Work includes a "NOTICE" text file, "any Derivative Works that You distribute must include a readable copy of the attribution notices contained within such NOTICE file" in a NOTICE file, in source or documentation, or in a display generated by the Derivative Works. (canonical text, not re-fetched) — [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- ASF guidance: NOTICE should hold only legally required notices, not general credits. (canonical guidance, not re-fetched) — [ASF: Assembling LICENSE and NOTICE](https://infra.apache.org/licensing-howto.html)
- MIT: "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software." (canonical text, not re-fetched) — [MIT License (OSI)](https://opensource.org/license/mit)
- BSD-3-Clause clause 2: "Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution." Clause 3: no use of contributors' names for endorsement. (canonical text, not re-fetched) — [BSD-3-Clause (OSI)](https://opensource.org/license/bsd-3-clause)
- emlearn is MIT licensed ("emlearn is MIT licensed"). The README says nothing about the license of generated C code. (fetched) — [emlearn GitHub](https://github.com/emlearn/emlearn)
- REUSE spec: every file needs `SPDX-FileCopyrightText` and `SPDX-License-Identifier` (in a header, a `.license` sidecar file, or `REUSE.toml` for files that cannot hold comments, such as weights), and full license texts go in `LICENSES/<SPDX-ID>.txt`; `reuse lint` checks this. (canonical spec, not re-fetched) — [REUSE specification](https://reuse.software/spec/)

### Inferences
- Generated C from emlearn has two parts. Model constants (tree thresholds, weights) come from your training and data. The runtime headers (`eml_*.h`) are emlearn's MIT code, compiled into the firmware. So: firmware and generated sources include the emlearn MIT notice. TensorFlow Lite Micro / LiteRT (Apache-2.0) needs its LICENSE and NOTICE content. scikit-learn (BSD-3) needs a notice only if its code or binaries ship, which is usually not the case for a trained model. (M)
- For data-derived constants in generated code, the data license attribution applies (Q1). A header comment listing datasets and licenses is cheap. (M)
- Imported Apache-2.0 code from other repos: keep the original headers, add "Modified by ... (year)" to changed files (§4(b)), and merge their NOTICE content into the repo NOTICE. (H)

### Gaps
- No official emlearn statement on the license of generated output was found. A human could ask the maintainer or check the emlearn docs or issues.
- The exact current TFLite Micro NOTICE content was not checked.

## Q4. LLM outputs as training data: Anthropic, OpenRouter and upstream providers, MiMo

### Takeaway
This is the highest-risk area. Anthropic's Consumer Terms (which cover Pro and Max subscriptions) ban using the services "to develop or train any artificial intelligence or machine learning algorithms or models" in a competing context. The Commercial Terms have a similar "competing AI models" bar. OpenAI and Google Gemini API ban using outputs or services to develop competing models. OpenRouter passes all output rights and restrictions on to each provider's "Model Terms". MiMo is MIT-licensed, so self-hosted MiMo outputs carry no contractual restriction. Confidence M-H on the clause texts; whether a small mobility classifier "competes" is unsettled and needs a human decision.

### Cited Findings
- Anthropic Consumer Terms (effective 8 Oct 2025), §3 prohibited uses: "To develop any products or services that compete with our Services, including to develop or train any artificial intelligence or machine learning algorithms or models or resell the Services." §3 also bans automated access without an API key. (fetched) — [Anthropic Consumer Terms](https://www.anthropic.com/legal/consumer-terms)
- Same terms, §4: "Subject to your compliance with our Terms, we assign to you all our right, title, and interest (if any) in Outputs." Anthropic may train on Materials unless you opt out. (fetched) — [Anthropic Consumer Terms](https://www.anthropic.com/legal/consumer-terms)
- Anthropic Commercial Terms (effective 17 June 2025), §D.4: Customer may not "access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic". §B: Customer "owns its Outputs". (fetched) — [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- OpenRouter Terms (last updated 31 Aug 2026), §6.1: "Your ownership rights in the Output are set forth in the Model Terms for each Model you use." §5.1: "You are solely responsible for reviewing the Model Terms applicable to each Model before accessing or using that Model." §7 bars use that violates Model Terms, and bars reselling or developing competing services (with respect to OpenRouter). (fetched) — [OpenRouter Terms](https://openrouter.ai/terms)
- OpenAI Terms of Use (effective 1 Jan 2026, per search snippet) ban using Output "to develop models that compete with OpenAI". The direct fetch returned 403, so this comes from the search snippet and an aggregator. — [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/); [ConductAtlas provision record](https://conductatlas.com/platform/openai/openai-eu-terms-of-use/no-use-of-output-to-compete-with-openai/)
- Gemini API Additional Terms (last updated 23 Mar 2026): "You may not use the Services to develop models that compete with the Services (e.g., Gemini API or Google AI Studio)." Google does not claim ownership of generated content. EEA/CH/UK: only Paid Services may be used when making API clients available to users there. (fetched) — [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- DeepSeek: one aggregator reports an "anti-distillation clause" in a DeepSeek model license. This is unverified and conflicts with my understanding that the DeepSeek-R1 weights are MIT-licensed and allow distillation; the hosted DeepSeek platform terms may differ from the open-weight license. — [ConductAtlas DeepSeek record](https://conductatlas.com/platform/deepseek/deepseek-model-license/anti-distillation-clause/) (low reliability)
- MiMo: Xiaomi released MiMo-V2-Flash, V2.5/V2.5-Pro and V2.6 (22 Sep 2026) weights under MIT on HF. (secondary sources) — [Wikipedia: Xiaomi MiMo](https://en.wikipedia.org/wiki/Xiaomi_MiMo); [Korben](https://korben.info/en/xiaomi-open-source-mimo-v2-5-pro-mit-license.html); [Origami](https://origami.sa/en/blog/xiaomi-mimo-v2-6-open-source-omnimodal-model/); [HF XiaomiMiMo](https://huggingface.co/XiaomiMiMo/MiMo-V2.5-DFlash)

### Inferences
- Claude via subscription: the Consumer Terms §3 clause is broad. Read literally, the second half ("including to develop or train any ... models") applies within "products or services that compete with our Services". A narrow mobility classifier arguably does not compete with Claude, but this is an interpretation risk. Separately, labeling large datasets through a consumer plan may hit the ban on automated access without an API key if done by script. Human decision: (a) accept the risk and document it; (b) move labeling to the API under the Commercial Terms (same "competing" test, but clearer for programmatic use); or (c) use MiMo or open-weight teachers for labels that end up in published models. (M)
- The harness must record per label or sample: teacher model ID, access path (consumer subscription / API / OpenRouter provider slug / local), and the date. Without this, provenance cannot be shown per provider. (H)
- OpenRouter: decide per upstream model. Allowlist open-weight models with permissive licenses (MIT, Apache-2.0: e.g. MiMo, many Qwen and Mistral open models; check each card). Flag closed models (OpenAI, Google, Anthropic via OpenRouter) as "competing-model clause, human review". (M)
- Output copyright: outputs from LLMs are likely not protected by copyright in the EU (no human author). The restriction is contractual and binds only the account holder, not downstream users. Still a breach risk for the owner. (M)

### Gaps
- The OpenAI page and the Usage Policies could not be fetched (403). Mistral, Qwen (Alibaba Cloud Model Studio) and DeepSeek platform terms were not verified.
- The Anthropic Usage Policy (AUP) was not fetched for model-training clauses.
- The exact MiMo LICENSE file text (copyright holder line needed for an MIT notice) was not fetched.

## Q5. Base-model license (XLM-R, MIT) obligations

### Takeaway
MIT requires keeping the copyright notice and permission text "in all copies or substantial portions". A fine-tune of xlm-roberta-large contains substantial portions of the weights, so ship the XLM-R MIT notice. Fine-tuned weights can be released under Apache-2.0 (or CC BY-SA 4.0 for the MIMII model). Confidence H.

### Cited Findings
- MIT notice condition (see Q3). — [MIT License (OSI)](https://opensource.org/license/mit)
- HF `base_model` field: "If your model is a fine-tune, an adapter, or a quantized version of a base model, you can specify the base model". This shows the model tree; the relation is inferred (`adapter`, `merge`, `quantized`, `finetune`) or set with `base_model_relation`. (fetched) — [HF model cards docs](https://huggingface.co/docs/hub/model-cards)

### Inferences
- Model card YAML: `base_model: FacebookAI/xlm-roberta-large`, `base_model_relation: finetune`. NOTICE: "Contains model weights derived from XLM-RoBERTa (FacebookAI/xlm-roberta-large), Copyright (c) Facebook, Inc. and its affiliates, MIT License" plus the MIT text in `LICENSES/MIT.txt`. Copy the exact copyright line from the upstream LICENSE. (H on structure, verify the text)
- XLM-R pretraining data (CC-100 from Common Crawl) adds no license duty that passes to us beyond MIT. (M)

### Gaps
- The exact copyright line in the HF repo of FacebookAI/xlm-roberta-large was not fetched.

## Q6. HF metadata and how HF displays attribution

### Takeaway
HF shows `license` (filterable), `base_model` (model tree), and `datasets` ("Datasets used to train:" with links, only for Hub datasets). HF has no structured field for TASL, so attribution must go in the card text and a NOTICE file. Confidence H.

### Cited Findings
- "Adding datasets to the metadata will add a message reading `Datasets used to train:` to your model page and link the relevant datasets, if they're available on the Hub." "You should use the Hub dataset identifier". (fetched) — [HF model cards docs](https://huggingface.co/docs/hub/model-cards)
- Custom license: `license: other`, `license_name`, `license_link` (may point to a LICENSE in the repo). (fetched) — [HF model cards docs](https://huggingface.co/docs/hub/model-cards)
- `library_name` must be set explicitly for repos created after August 2024. (fetched) — [HF model cards docs](https://huggingface.co/docs/hub/model-cards)

### Inferences
- Datasets that are not on the Hub (Zenodo, DTU, UCI) are not linked by `datasets:`. Either republish them on HF (Q2) or list them only in the card text. Do not put non-Hub URLs into `datasets:`, which expects Hub IDs. (M)
- HF `license` takes one value. For mixed-license repos, set the license of the main artifact (the weights) and explain the others in the card and REUSE metadata. (M)

### Gaps
- The full HF modelcard.md spec (e.g. whether `license` accepts a list) was not fetched.

## Q7. License compatibility matrix (data into one model)

### Takeaway
CC BY 4.0 data can be combined freely; the model can use any license as long as attribution is kept. Any BY-SA input forces CC BY-SA 4.0 (or a compatible license) on the model (conservative reading). Web-scraped text with unknown licenses is the open item: it depends on the TDM exception and machine-readable opt-outs, not on CC. Confidence M.

### Cited Findings
- BY-SA §3(b): adapted material must use the same License Elements, a later version, or a BY-SA Compatible License. — [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
- CC FAQ: BY-SA 4.0 is one-way compatible with GPLv3. (fetched, summarized) — [CC FAQ](https://creativecommons.org/faq/)
- CC: models "based on ShareAlike content" that are "shared publicly" should use the same CC license. — [CC AI training guide](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)

### Inferences
Matrix (rows = training inputs, column = allowed model license under the conservative reading):

| Inputs | Apache-2.0 model | CC BY 4.0 model | CC BY-SA 4.0 model | Duties |
|---|---|---|---|---|
| MIT base (XLM-R) only | yes | yes | yes | MIT notice |
| + CC BY 4.0 data (ROAD, can-train-and-test, UCI HAR) | yes | yes | yes | TASL per dataset + modification note |
| + CC BY-SA 4.0 data (MIMII) | no (conservative) | no | yes (required) | TASL + same license; no extra terms or gating |
| + LLM labels (Claude / closed models) | contract question, not a license question | same | same | ToS review per provider (Q4) |
| + LLM labels (MiMo, MIT; other open-weight) | yes | yes | yes | MIT notice if the license is treated as covering outputs (conservative) |
| + web-scraped text | TDM exception plus opt-out check (other researcher) | same | same | record robots or TDM opt-outs |

- Never mix MIMII into a model meant to be Apache-2.0. Enforce this through the harness. (H)
- Apache-2.0 code combined with BY-SA weights in one repo is fine as an aggregate if per-file licensing is clear. (M)

### Gaps
- No case law on whether label data (LLM outputs) carries the LLM's license or ToS onto the student model.

## Q8. What the harness should generate and validate (enforceable rules, plus human decisions)

### Takeaway
Use one machine-readable provenance manifest per model as the single source of truth. Generate the HF YAML, card attribution table, NOTICE, REUSE metadata and SPDX expressions from it, and block release on rule violations. Confidence H for the design (derived from the cited license requirements above).

### Cited Findings
- CC §3(a)(2) allows attribution "in any reasonable manner based on the medium, means, and context", including a link to a resource with the information. This supports generated attribution pages. — [CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode.en)
- REUSE: `REUSE.toml` and `LICENSES/` plus `reuse lint`. — [REUSE spec](https://reuse.software/spec/)
- HF metadata fields `license`, `license_name`, `license_link`, `base_model`, `base_model_relation`, `datasets`. — [HF model cards docs](https://huggingface.co/docs/hub/model-cards)
- Apache §4(d) NOTICE propagation. — [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

### Inferences (proposed rule set)

**Manifest (`provenance.yaml` per model)**, one entry per input. Fields:
- `id`, `kind` (dataset / base_model / code / teacher / library)
- `title`, `creators`, `copyright_notice`
- `source_uri` and DOI, `retrieved_at`, `version` or checksum
- `license_spdx` (e.g. `CC-BY-4.0`, `CC-BY-SA-4.0`, `MIT`, `Apache-2.0`, `BSD-3-Clause`), `license_uri`
- `modifications` (free text)
- `citation_bibtex`
- for teachers: `access_path` (consumer / API / openrouter:<provider> / local) and `terms_snapshot_url` plus `terms_checked_at`

**Generated artifacts:**
1. HF YAML: `license` (SPDX lower-case HF ID, or `other` plus name and link), `base_model`, `base_model_relation`, `datasets` (Hub IDs only), `library_name`.
2. Model card section "Training data and attribution": a table with title, creator, copyright, license plus link, source link, modifications, and the disclaimer line "Provided as-is; see license for warranty disclaimer".
3. Model card section "Teacher / labeling models": provider, access path, terms version.
4. `NOTICE`: Apache §4(d) content from imported code, MIT notices (XLM-R, emlearn, MiMo if used), BSD-3 (if any binary ships), and CC attributions.
5. `LICENSES/*.txt` plus `REUSE.toml` (weights and data files annotated, because they cannot hold headers).
6. A header comment in generated C/firmware sources: emlearn MIT notice plus data attribution.
7. SPDX summary of the declared license per artifact (e.g. weights `CC-BY-SA-4.0`, code `Apache-2.0`).

**Blocking validations:**
- R1: any input with `license_spdx` containing `-SA-` means the weights license must equal `CC-BY-SA-4.0` (or a later version).
- R2: every CC input needs non-empty `creators`, `license_uri`, `source_uri`, `modifications`.
- R3: every MIT, BSD or Apache input needs `copyright_notice`, and its text must appear in NOTICE (BSD only if binaries ship).
- R4: HF `license` must equal the manifest's weights license. `base_model` must match the base_model entry.
- R5: `reuse lint` passes.
- R6: no license outside an allowlist {CC-BY-4.0, CC-BY-SA-4.0, CC0-1.0, MIT, Apache-2.0, BSD-2/3-Clause}. NC and ND licenses block release.
- R7: teacher entries with access_path in {consumer, a closed provider's API, openrouter:<closed provider>} block release until a human sign-off is recorded (`tos_review: approved_by, date`).
- R8: a BY-SA model repo must not be gated with extra terms (§3(b)).
- R9: republished datasets keep the original license; the card carries the citation and the modification note.
- R10: terms snapshots older than N months trigger re-review (terms change: OpenRouter updated 31 Aug 2026, Gemini Mar 2026, OpenAI Jan 2026).

**Decisions that need a human:**
- H1: Whether to use Claude (consumer plan) labels in published models, given Consumer Terms §3. Options: accept and document, switch to the API, or re-label with MiMo or open models.
- H2: Accept the per-provider OpenRouter risk for closed models, or restrict to open-weight models.
- H3: Re-host datasets on HF or only link them. Includes a GDPR check of CAN data (vehicle identifiers).
- H4: Whether to adopt the conservative "weights = Adapted Material" reading (recommended) or rely on the TDM exception.
- H5: Licensing of web-scraped text corpora (handled by the TDM / opt-out researcher).
- H6: Whether to ask emlearn's maintainer about the license of generated code.

### Gaps
- The harness design is my own synthesis. No external standard for "AI provenance manifests" was surveyed (e.g. SPDX 3.0 AI/Dataset profiles, which would be a natural format; not fetched).
