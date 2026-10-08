# EU AI Act (Regulation (EU) 2024/1689) applied to a one-person open-source mobility model zoo (DE), status 2026-10-08

Not legal advice. Confidence: High / Medium / Low per conclusion. "Inference" = my own reasoning from cited text, not a source statement. Main source for the legal text is the consolidated reader at artificialintelligenceact.eu, because EUR-Lex HTML did not render in the fetch tool. Spot-check the quotes against EUR-Lex (https://eur-lex.europa.eu/eli/reg/2024/1689/oj) before relying on them.

## Q1. GPAI model, AI system, or neither?

### Takeaway
None of the models is a general-purpose AI model. scout-large is an encoder token classifier for one narrow task, it does not generate, and its estimated compute is below 10^23 FLOP (High). The deployable artefacts (scout-large plus inference code, the CAN IDS, MIMII and HAR models) most likely meet the Art. 3(1) definition of an "AI system", or are components of one, because they are ML models that infer outputs (predictions, classifications) from inputs (Medium-High). Bare weights without a system around them are "AI models", which the Act regulates only as GPAI (Medium; unsettled).

### Cited Findings
- Art. 3(63): a GPAI model is "an AI model ... that displays significant generality and is capable of competently performing a wide range of distinct tasks regardless of the way the model is placed on the market". — [AI Act Art. 3](https://artificialintelligenceact.eu/article/3/)
- Art. 3(1): an AI system is "a machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers, from the input it receives, how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments". — [AI Act Art. 3](https://artificialintelligenceact.eu/article/3/)
- The GPAI guidelines (July 2025) set an indicative criterion: a model "trained using more than 10²³ FLOPs" that can generate language (text or audio), text-to-image or text-to-video is presumed GPAI. A model of about 1B parameters trained on a large dataset would typically reach this. — [artificialintelligenceact.eu GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/); primary: [Commission guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-scope-obligations-providers-general-purpose-ai-models-under-ai-act)
- The guidelines exclude narrow models that fail the "functional generality requirement" even when they pass the compute threshold. Examples: transcription, image upscaling, weather forecasting, game-specific models. — [GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/)
- Compute estimates must be accurate to within ±30%, with assumptions documented. Forward passes that generate synthetic data count toward training compute. Failed experiments and diagnostics do not. — [GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/)
- The Commission's AI-system-definition guidelines (Feb 2025) exclude "basic data processing", "simple prediction systems" (performance achievable with a basic statistical rule, e.g. last week's average temperature) and "classical heuristics". — [CMS summary](https://cms.law/en/gbr/legal-updates/eu-commission-issues-guidelines-on-the-definition-of-ai-systems)
- Recital 97: AI models used "before their placing on the market for the sole purpose of research, development and prototyping activities" are not covered by the GPAI definition. — [Recital 97](https://artificialintelligenceact.eu/recital/97/)

### Inferences
- scout-large compute (my estimate, verify): XLM-R-large pretraining is about 6 × 5.6e8 params × ~6e12 tokens ≈ 2e22 FLOP, below 1e23. Fine-tuning on a few tens of millions of tokens is about 1e17 FLOP. Teacher-LLM labelling forward passes might count as "synthetic data generation" for the labeller, but they run on third-party models and do not change the analysis. The model also lacks the generative-modality element and the generality. Not GPAI. Confidence: High.
- The base model (XLM-R) is probably not GPAI either: it is a masked-LM encoder under 1e23 and was placed on the market before 2 Aug 2025. So the "downstream modifier becomes GPAI provider" rule does not apply (High).
- CAN-IDS random forest and int8 MLP, MIMII autoencoder, HAR CNN: all are learned models that infer classifications or anomaly scores. They are not "simple prediction systems" in the guideline sense, provided they beat trivial baselines. So when shipped as a runnable system (firmware or inference code with an intended purpose) they are AI systems. Confidence: Medium-High. The harness should record a trivial-baseline comparison as evidence either way.
- Whether a weights-only release of a narrow model is an "AI system" or only a model (which the Act regulates only if GPAI) is unsettled. Practical approach: treat each published repo with inference code and an intended purpose as an AI system or component and rely on Art. 2(12) (see Q3). Confidence: Medium.

### Gaps
- I did not fetch the full text of the AI-system-definition guidelines. I did not find any treatment there of "weights only" vs "system".
- I did not obtain exact XLM-R pretraining compute from a primary source. The figure above is my estimate.

## Q2. If GPAI: Art. 53, open-source exemption, what remains, modifiers

### Takeaway
This is not triggered for the current models (High). If a future model became GPAI, the Art. 53(2) open-source exemption would drop only Art. 53(1)(a) and (b) (technical documentation, downstream info). The copyright policy (53(1)(c)) and the public training-content summary on the AI Office template (53(1)(d)) would still apply, as would the EU-representative duty for non-EU providers (Art. 54). A fine-tuner becomes provider only if the modification compute exceeds one third of the original model's training compute.

### Cited Findings
- Art. 53(1)(c): providers must "put in place a policy to comply with Union law on copyright and related rights, and in particular to identify and comply with, including through state-of-the-art technologies, a reservation of rights expressed pursuant to Article 4(3) of Directive (EU) 2019/790". — [Art. 53](https://artificialintelligenceact.eu/article/53/)
- Art. 53(1)(d): providers must "draw up and make publicly available a sufficiently detailed summary about the content used for training ... according to a template provided by the AI Office". — [Art. 53](https://artificialintelligenceact.eu/article/53/)
- Art. 53(2): points (a) and (b) "shall not apply to providers of AI models that are released under a free and open-source licence that allows for the access, usage, modification, and distribution of the model, and whose parameters, including the weights, the information on the model architecture, and the information on model usage, are made publicly available". This does not apply to GPAI models with systemic risk. — [Art. 53](https://artificialintelligenceact.eu/article/53/)
- Licence conditions in the guidelines: the licence must allow use, access, modification and redistribution. Non-commercial-only terms, redistribution bans, user-size thresholds or mandatory commercial licences disqualify it. Attribution, same-licence distribution and non-discriminatory safety-use restrictions are allowed. — [GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/)
- Monetisation indicators that remove the exemption: dual licensing, paid support/maintenance/updates, hosted access for fees or advertising revenue, mandatory payment for essential functionality. Optional premium services that leave free core access in place are not monetisation. — [GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/)
- Recital 103: components "provided against a price or otherwise monetised, including through the provision of technical support or other services" lose the open-source exception. "The fact of making AI components available through open repositories should not, in itself, constitute a monetisation". Transactions between microenterprises are carved out. — [Recital 103](https://artificialintelligenceact.eu/recital/103/)
- Modifier rule: a downstream modifier becomes the GPAI provider if modification compute is ≥ 1/3 of the original training compute (indicatively ≥ 1/3 × 10^23 FLOP; ≥ 1/3 × 10^25 for systemic risk). Its obligations are then limited to the modification (documentation, data summary and copyright policy for the added data and compute). — [GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/)
- Timeline: GPAI obligations apply from 2 Aug 2025. The Commission's enforcement powers (fines) start 2 Aug 2026. Models placed on the market before 2 Aug 2025 have until 2 Aug 2027. — [Commission GPAI guidelines page](https://digital-strategy.ec.europa.eu/en/policies/guidelines-gpai-providers)
- Training-content template (published 24 Jul 2025) has three sections: general info (provider, model, modalities, size per modality), list of data sources (public datasets, licensed and unlicensed private data, web-scraped data, user data, synthetic data), and other processing aspects. For scraped data it asks for crawler details, collection period, and the top 10% of domains by content size. — [WilmerHale](https://wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/european-commission-releases-mandatory-template-for-public-disclosure-of-ai-training-data); [Commission FAQ](https://digital-strategy.ec.europa.eu/en/faqs/template-general-purpose-ai-model-providers-summarise-their-training-content)

### Inferences
- Even though Art. 53 does not apply, the project can adopt a voluntary "training-content summary" modelled on the template (sources, scraped domains top-10%, crawl window, teacher LLMs as synthetic-label sources) and a copyright/TDM-opt-out policy. Cost is low, and it future-proofs a later GPAI release (e.g. a generative scout). Copyright compliance for scraping is required anyway under DSM Directive Art. 4(3), German UrhG §44b, independent of the AI Act (Medium; outside this file's scope).
- Releasing under Apache-2.0/MIT with public weights and no paid tiers meets the open-source conditions. A "non-commercial" licence (e.g. CC-BY-NC, inherited from datasets such as MIMII or UCI HAR terms) would break the exemption logic and the Art. 2(12) exclusion. The harness should block NC licences on model artefacts (High).
- Donation buttons (GitHub Sponsors) are not listed as monetisation indicators. Treat them as low risk but flag them (Low-Medium, unsettled).

### Gaps
- I did not verify verbatim in the primary PDF the guidelines' wording on the 1/3 threshold when original compute is unknown (reportedly falls back to 1/3 of 1e23).

## Q3. Art. 2(12) open-source exclusion; Art. 2(6)/(8) research exclusions

### Takeaway
Art. 2(12) excludes AI systems released under free and open-source licences from the whole Regulation unless they are placed on the market or put into service as high-risk, as an Art. 5 practice, or as an Art. 50 system. None of the zoo's models falls in those categories (see Q5/Q6), so the exclusion very likely covers them (Medium-High). The research exclusions (2(6), 2(8)) do not cover publicly released models intended for use by others (High).

### Cited Findings
- Art. 2(12): "This Regulation does not apply to AI systems released under free and open-source licences, unless they are placed on the market or put into service as high-risk AI systems or as an AI system that falls under Article 5 or 50." — [Art. 2](https://artificialintelligenceact.eu/article/2/)
- Art. 2(6): does not apply to AI systems or models "specifically developed and put into service for the sole purpose of scientific research and development". — [Art. 2](https://artificialintelligenceact.eu/article/2/)
- Art. 2(8): does not apply to "any research, testing or development activity ... prior to their being placed on the market or put into service ... Testing in real world conditions shall not be covered by that exclusion." — [Art. 2](https://artificialintelligenceact.eu/article/2/)
- Art. 2(12) covers AI systems only. GPAI models get the narrower Art. 53(2) / 54(6) carve-outs. — [Art. 53](https://artificialintelligenceact.eu/article/53/), inference from structure of [Art. 2](https://artificialintelligenceact.eu/article/2/)

### Inferences
- Public release "intended to be commercially usable by others" contradicts "sole purpose of scientific research". Art. 2(6) is not available. Art. 2(8) covers only the pre-release development phase, e.g. internal training runs and experiments before upload (High).
- Art. 2(12) is lost if the project markets a model "as" high-risk, e.g. a model card saying "for use as a vehicle safety system" or "for recruitment screening". Intended-purpose wording in model cards is therefore the main compliance lever. The harness should lint model cards for Annex III / safety-component purpose claims (High).

### Gaps
- No official Commission guidance found on how Art. 2(12) interacts with a "commercial activity" requirement for non-commercial individuals.

## Q4. Provider / placing on the market; private individual in scope?

### Takeaway
A natural person can be a "provider" (Art. 3(3)). For GPAI, the Commission says uploading to a repository is placing on the market and the uploader is the provider (High). For AI systems, "making available" requires supply "in the course of a commercial activity, whether in return for payment or free of charge". Whether a non-monetising hobbyist's free uploads count as commercial activity is unsettled (Low-Medium). Plan as if in scope and rely on Art. 2(12).

### Cited Findings
- Art. 3(3): provider is "a natural or legal person ... that develops an AI system or a general-purpose AI model ... and places it on the market or puts the AI system into service under its own name or trademark, whether for payment or free of charge" (the last clause is in the Act's text; the fetched excerpt was truncated). — [Art. 3](https://artificialintelligenceact.eu/article/3/)
- Art. 3(9): placing on the market = "the first making available of an AI system or a general-purpose AI model on the Union market". Art. 3(10): making available = supply "in the course of a commercial activity, whether in return for payment or free of charge". Art. 3(11): putting into service = "supply of an AI system for first use directly to the deployer or for own use in the Union for its intended purpose". — [Art. 3](https://artificialintelligenceact.eu/article/3/)
- Recital 97: GPAI models are placed on the market "through libraries, application programming interfaces (APIs), as direct download, or as physical copy". — [Recital 97](https://artificialintelligenceact.eu/recital/97/)
- GPAI guidelines: uploading to a repository is placing on the market, and the uploader remains provider unless EU use is explicitly excluded. Repositories (e.g. HF) do not take over provider status. — [GPAI guidelines overview](https://artificialintelligenceact.eu/gpai-guidelines-overview/)
- Art. 2(10): deployer obligations do not apply to natural persons using AI "in the course of a purely personal non-professional activity". This exemption covers deployers only, not providers. — [Art. 2](https://artificialintelligenceact.eu/article/2/)

### Inferences
- Treat the owner as "provider" of each published model, identified by the HF/GitHub account name ("under its own name"). Confidence: Medium. Owner's own use in demos or benchmarks is not "putting into service" for a deployer, and it is non-professional.
- Monetisation (paid consulting tied to the models, sponsorship with perks, paid hosted API) would both strengthen the "commercial activity" reading and endanger the open-source carve-outs. Log any revenue streams in the classification record.

### Gaps
- I found no AI Office / AI Act Service Desk FAQ explicitly addressing private individuals publishing free models. The Blue Guide's "commercial activity" concept (EU product law) likely governs, but I did not fetch it.

## Q5. High-risk: CAN intrusion detector and the others

### Takeaway
The CAN IDS is very unlikely to be high-risk as published (Medium-High). (1) A cybersecurity-only component is expressly not a "safety component" per Recital 55 (stated for critical infrastructure). The digital omnibus also narrowed "safety component" to require an intended purpose of preventing or mitigating health and safety risks. (2) Vehicle type-approval law (2018/858, 2019/2144) sits in Annex I Section B. For those products only Art. 6(1), 102–109 and 112 of the AI Act apply: AI requirements reach vehicles only through future delegated or implementing acts under the type-approval regulations, addressed to vehicle and component manufacturers in type approval, not to a GitHub publisher. (3) Annex I high-risk application moved to 2 Aug 2028 under the adopted digital omnibus. MIMII anomaly detection and HAR are not in Annex III as published (Medium-High).

### Cited Findings
- Art. 3(14): safety component = component that "fulfils a safety function for that product or AI system, or the failure or malfunctioning of which endangers the health and safety of persons or property". — [Art. 3](https://artificialintelligenceact.eu/article/3/)
- Recital 55: "Components intended to be used solely for cybersecurity purposes should not qualify as safety components." (context: Annex III point 2 critical infrastructure) — [Recital 55](https://artificialintelligenceact.eu/recital/55/)
- Art. 2(2): for high-risk AI systems under Art. 6(1) related to products under Annex I Section B legislation, "only Article 6(1), Articles 102 to 109 and Article 112 apply". — [Art. 2](https://artificialintelligenceact.eu/article/2/)
- Art. 107 amends Regulation (EU) 2018/858 and Art. 109 amends Regulation (EU) 2019/2144. They require AI Act Chapter III Section 2 requirements to be taken into account in delegated or implementing acts on AI safety components. — [artificialintelligenceact.eu, Art. 108 page summary](https://artificialintelligenceact.eu/article/108/)
- Digital omnibus (adopted): "safety component" narrowed to require an "intended purpose of preventing or mitigating risks to health and safety". Non-safety user-assistance systems are excluded, but systems whose failure endangers human health still qualify. — [Orrick, July 2026](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes)
- Digital omnibus: Annex III high-risk obligations moved from 2 Aug 2026 to 2 Dec 2027. Annex I / Art. 6(1) moved from 2 Aug 2027 to 2 Aug 2028. — [Orrick](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes); [Jones Walker](https://www.joneswalker.com/en/insights/blogs/ai-law-blog/yes-august-2-still-matters-the-eu-approved-a-high-risk-ai-delay-but-most-trans.html?id=102nbon); [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-omnibus-vii-deadline-delay-20260/)

### Inferences
- R155 (UNECE cyber management system) is imposed via 2019/2144 type approval. An IDS supports R155 compliance, but its function is detection of attacks, not a direct safety function. Counter-argument: an IDS that actively blocks frames or triggers a safe state could have failure modes that endanger safety. That would push it toward a safety component. Keep the published intended purpose to "research/reference detection, monitoring and logging, not an active safety mechanism" (Medium; unsettled).
- Annex III point 2 (safety components in management and operation of road traffic / critical infrastructure) targets traffic infrastructure, not in-vehicle ECUs. Recital 55 also carves out cybersecurity-only components (Medium-High).
- MIMII (industrial machine sound anomaly): could be a machinery safety component under Annex I Section A (Machinery Regulation 2023/1230) if marketed as a safety function. As a condition-monitoring reference model it is not one (Medium). HAR: not Annex III unless marketed for workplace monitoring of employees (Annex III point 4) or for biometric/emotion purposes. Model-card wording matters (Medium).
- scout-large (jobs/pains/gains extraction): not Annex III unless marketed for recruitment, worker evaluation, or creditworthiness (Medium-High).

### Gaps
- No Commission high-risk classification guidelines (Art. 6(5)) found or fetched in this session. Check whether they were published and whether they address automotive IDS.
- No delegated acts under 2018/858 / 2019/2144 integrating AI requirements found. Status unknown.

## Q6. Art. 50 transparency and Art. 4 AI literacy

### Takeaway
Art. 50 does not apply to any model here, since none interacts with people as a chatbot or generates synthetic audio/image/video/text (High). Art. 4 applies to providers and deployers of AI systems. As amended by the omnibus, it now requires only measures to "support" AI literacy of staff and persons acting on their behalf. A one-person non-employer has essentially nothing to do beyond documenting their own competence and giving usage guidance (Medium). Under Art. 2(12), open-source systems are arguably out of scope for Art. 4 entirely (Medium).

### Cited Findings
- Art. 50 obligations (AI-interaction disclosure, synthetic-content marking, emotion/biometric notices, deepfakes, public-interest text) apply from 2 Aug 2026. Providers of systems placed on the market before 2 Aug 2026 get until 2 Dec 2026 for Art. 50(2) marking. — [Jones Walker](https://www.joneswalker.com/en/insights/blogs/ai-law-blog/yes-august-2-still-matters-the-eu-approved-a-high-risk-ai-delay-but-most-trans.html?id=102nbon). Orrick describes the 2 Dec 2026 grace period more generally, without the legacy-only limit: [Orrick](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes). Minor conflict.
- Omnibus (in force 27 Jul 2026) rewrote Art. 4 from "ensure a sufficient level" of AI literacy to "take measures to support" its development. Commission and Member States are to support implementation. — [KI-Campus](https://ki-campus.org/en/blog/eu-ai-act-ai-omnibus-recalibrates-article-4-ai-literacy-remains-mandatory); [9am.works](https://www.9am.works/freelancer-academy/blog/eu-ai-act-article-4-ai-literacy-freelancers-2026)

### Inferences
- If a future scout variant generates text (e.g. a generative summariser), Art. 50(2) machine-readable marking would apply, and Art. 2(12) would no longer exclude it. The harness should flag any generative output head (High).

### Gaps
- I did not fetch the amended Art. 4 text from the OJ.

## Q7. Timelines and changes adopted by Oct 2026

### Takeaway
Original: 2 Feb 2025 (Art. 1–5, prohibitions, AI literacy); 2 Aug 2025 (GPAI, governance, penalties); 2 Aug 2026 (general application, Art. 50, Annex III); 2 Aug 2027 (Art. 6(1)/Annex I; GPAI legacy models). The Digital Omnibus on AI was adopted and in force as of 27 Jul 2026. It moved Annex III to 2 Dec 2027 and Annex I to 2 Aug 2028, added a 2 Dec 2026 grace period for Art. 50(2) and new Art. 5 prohibitions from 2 Dec 2026, softened Art. 4, narrowed "safety component", and added SMC relief. GPAI timelines are unchanged (High for adoption; Medium for details).

### Cited Findings
- Political agreement 7 May 2026. EP endorsement 16 Jun 2026. Council adoption 29 Jun 2026. OJ publication 24 Jul 2026. In force 27 Jul 2026. — [Usercentrics / search summary](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/); [Formalize](https://formalize.com/en/blog/eu-ai-act-digital-omnibus)
- Orrick gives the OJ reference as "Regulation (EU) 2026/1744". This is single-source and not verified on EUR-Lex. — [Orrick](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes)
- New Art. 5 prohibitions from 2 Dec 2026: non-consensual intimate imagery ("nudifier") and CSAM generation. SMC relief for companies under 750 employees and ≤ €150M turnover. AI Office gains exclusive supervision of GPAI-model-based systems. — [Orrick](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes)
- GPAI, prohibitions and general transparency keep their original timeline. — [Usercentrics](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/)
- GPAI enforcement powers from 2 Aug 2026. Legacy GPAI until 2 Aug 2027. — [Commission](https://digital-strategy.ec.europa.eu/en/policies/guidelines-gpai-providers)

### Inferences
- None of the omnibus changes create new duties for this project. The narrowed safety-component definition and the Annex I delay reduce CAN-IDS risk further.

### Gaps
- Regulation number and exact amended article texts not verified on EUR-Lex. The harness should store a pointer to the consolidated text version checked.
- Whether the omnibus changed Art. 2(12) or Art. 53(2): no source mentions any change. Presumed unchanged.

## Q8. GPAI Code of Practice copyright chapter; relevance for non-signatories

### Takeaway
In the copyright chapter, signatories commit to a copyright policy, to crawling only lawfully accessible content without circumventing protection measures, to excluding piracy domains, to honouring robots.txt and other machine-readable TDM opt-outs, to mitigating infringing outputs, and to a complaints contact. Non-signatories are not bound, but these measures are the de facto benchmark of "state of the art" for Art. 53(1)(c) and for DSM Art. 4(3) opt-out compliance (Medium). Useful as a scraper checklist for scout's web-scraped corpus.

### Cited Findings
- The copyright chapter is one of three (transparency, copyright, safety and security). It requires reproducing only lawfully accessible works, not circumventing technological measures, excluding piracy-focused domains (reasonable efforts not to crawl them), and using crawlers that read and follow the Robot Exclusion Protocol (robots.txt). — [Slaughter and May](https://thelens.slaughterandmay.com/post/102ktcs/mining-the-copyright-chapter-of-the-gpai-code); [Freshfields](https://technologyquotient.freshfields.com/post/102ksv0/the-final-general-purpose-ai-code-of-practice-a-short-guide)

### Inferences
- The scraper logs should record the robots.txt decision per URL and the TDM-reservation check (robots.txt, ai.txt / TDMRep headers, ToS). The Code also mentions an EU piracy-domain list (EUIPO-related list in the final Code; not verified here). The harness can enforce a domain denylist.

### Gaps
- Final Code text not fetched. Measure numbering and the piracy-list reference not verified.

## Q9. Harness checks, human decisions, classification record

### Takeaway
A one-person zoo can automate most of the evidence: licence, open weights, no monetisation, intended-purpose wording, compute estimate, generative capability flag, training-source summary, robots/TDM logs. Classification calls (AI system vs model, high-risk intended purpose, safety component) need a recorded human decision with a date and a re-review trigger.

### Inferences (design, derived from Q1–Q8)
Automated checks (fail release on violation):
1. Licence on weights, code and card is OSI/FSF-approved permissive or copyleft. No NC/ND/RAIL-style use bans beyond non-discriminatory safety clauses. Dataset licences are compatible (MIMII and UCI HAR terms to be checked).
2. Weights, architecture info and usage info public (HF repo not gated or paid).
3. No monetisation markers: no paid tier, paid API, or dual licence in README/FUNDING files. Sponsorship flagged for human review.
4. Model card "intended use" / "out-of-scope" lint: deny-list of Annex III terms (recruitment, hiring, credit, education scoring, biometric, emotion, law enforcement, migration, critical-infrastructure safety) and of "safety function", "vehicle safety", "ASIL" claims. Required out-of-scope statement for CAN IDS: "not a safety component; not type-approved; monitoring/research reference only".
5. Compute estimate (6·N·D plus teacher-generation note, ±30% assumptions) recorded. Alert if > 3.3e22 (1/3 of 1e23) or > 1e23.
6. Generative-output flag (any text/audio/image generation head), which would trigger Art. 50 and GPAI review.
7. Training-content summary generated in the AI Office template structure: sources, top-10% scraped domains, crawl period, teacher LLMs used for labels.
8. Scrape-log audit: robots.txt compliance rate 100%, TDM opt-out respected, piracy-domain denylist hits = 0.
9. Trivial-baseline comparison stored, as evidence for or against "simple prediction system".
10. Legal-reference freshness: date and version of AI Act consolidated text and guidelines last checked. Fail if older than N months.

Human decisions (recorded, signed and dated by owner):
- AI system vs model-only classification. GPAI yes/no (rationale). High-risk yes/no with Annex reference. Safety-component yes/no. Revenue/monetisation status. Re-review triggers (new modality, size > 1B params, new intended use, deployment partner in automotive).

Recommended per-model "AI Act classification record" fields:
- `model_id`, `version`, `release_date`, `provider_name` (natural person), `provider_country` (DE), `release_channels` (HF, GitHub)
- `artefact_type` (weights_only | weights+inference_code | firmware), `ai_system_assessment` (yes/no/component + rationale + guideline ref), `trivial_baseline_delta`
- `gpai_assessment`: `params`, `training_compute_flop_est`, `compute_method`, `base_model`, `base_model_compute_est`, `modification_compute_ratio`, `generative_capability` (bool), `generality_rationale`, `is_gpai` (bool), `systemic_risk` (bool)
- `licence_weights`, `licence_code`, `licence_osi_ok` (bool), `dataset_licences`, `weights_public`, `architecture_public`, `usage_info_public`, `monetisation` (none/donations/other + details)
- `exclusion_basis` (Art 2(12) / Art 2(8) pre-release / none), `exclusion_blockers_checked` (Art 5, Art 50, high-risk)
- `intended_purpose`, `out_of_scope_uses`, `annex_iii_match` (none / point + rationale), `annex_i_legislation` (e.g. 2018/858, 2019/2144, 2023/1230 / none), `safety_component` (bool + rationale incl. Recital 55), `high_risk` (bool), `applicable_from` (2 Dec 2027 / 2 Aug 2028 / n.a.)
- `art50_trigger` (bool), `art4_measures` (usage guidance link)
- `training_content_summary_link`, `copyright_policy_link`, `robots_tdm_compliance` (stats), `piracy_denylist_version`, `teacher_models` (Claude, OpenRouter models, MiMo; plus their ToS on output use)
- `legal_basis_version` (AI Act consolidated incl. omnibus, OJ ref, guidelines dates), `reviewed_by`, `review_date`, `next_review_trigger`, `confidence`

### Gaps
- Teacher-LLM terms of service (output use for training competing models) are outside the AI Act but relevant. Not researched here.
