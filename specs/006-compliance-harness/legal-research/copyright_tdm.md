# Copyright, TDM and database-right obligations (EU/Germany) for the Mobility Model Zoo

Status: research notes as of 2026-10-08. Not legal advice. Confidence: High / Medium / Low per conclusion. "UNSETTLED" marks open law or pending appeals.

Project facts assumed: one private individual in Germany; non-commercial open-source project; models meant to be commercially usable by third parties; text model trained on scraped forums, reviews, papers, parliamentary records, reports; raw snapshots kept locally, never published; verbatim quotes are part of the model's output format; model cards show fictional examples and evaluation results; other models trained on public datasets (Zenodo, UCI, Bitbucket, DTU); a curated third-party dataset compendium on Hugging Face is under consideration.

## Q1: §44b UrhG (Art. 4 DSM Directive) vs §60d UrhG (Art. 3): conditions, who qualifies, retention, lawful access

### Takeaway
§44b is the realistic legal basis for this project. It is open to anyone, including commercial actors, but it requires lawful access, respect for machine-readable opt-outs, and deletion once copies are no longer needed for TDM. §60d (no opt-out, longer retention) covers "individual researchers" only if they pursue non-commercial purposes. A private open-source developer whose stated aim is commercially usable models is a weak §60d case. Confidence: High on the text of the law, Medium on the §60d classification.

### Cited Findings
- §44b(1) defines TDM as "die automatisierte Analyse von einzelnen oder mehreren digitalen oder digitalisierten Werken, um daraus Informationen insbesondere über Muster, Trends und Korrelationen zu gewinnen." — [§44b UrhG](https://www.gesetze-im-internet.de/urhg/__44b.html)
- §44b(2): copies of **lawfully accessible** works are permitted for TDM; the copies **must be deleted once no longer needed** for TDM. — [§44b UrhG](https://www.gesetze-im-internet.de/urhg/__44b.html)
- §44b(3): the use is permitted only if the rightsholder has not reserved it; "Ein Nutzungsvorbehalt bei online zugänglichen Werken ist nur dann wirksam, wenn er in maschinenlesbarer Form erfolgt." — [§44b UrhG](https://www.gesetze-im-internet.de/urhg/__44b.html)
- §60d(1): TDM copies (§44b(1) and (2) sentence 1) are permitted for scientific research. Note that it references only §44b(2) sentence 1: the deletion duty in sentence 2 and the opt-out in (3) do not apply. — [§60d UrhG](https://www.gesetze-im-internet.de/urhg/__60d.html)
- §60d(2): entitled are research organisations that are non-commercial, reinvest all profits in research, or act under a state-recognised public-interest mandate. Organisations cooperating with a private company that has a "determining influence" are excluded. §60d(3): also libraries, museums, archives, heritage institutions, and **"einzelne Forscher, sofern sie nicht kommerzielle Zwecke verfolgen"** (individual researchers pursuing non-commercial purposes). — [§60d UrhG](https://www.gesetze-im-internet.de/urhg/__60d.html)
- §60d(4): non-commercial beneficiaries may make the copies available to a **specifically delimited circle of persons** for joint research and to individual third parties for quality verification. Access must end when the project ends. This is not public release. — [§60d UrhG](https://www.gesetze-im-internet.de/urhg/__60d.html)
- §60d(5): the copies may be kept, with appropriate security measures, as long as needed for research or for verifying results. — [§60d UrhG](https://www.gesetze-im-internet.de/urhg/__60d.html)
- OLG Hamburg (10.12.2025, 5 U 104/24) treated the creation of the LAION dataset as research ("applied research" with methodical, verifiable procedures aimed at future knowledge gains). That commercial entities could later use the dataset did not disqualify LAION, absent a "bestimmender Einfluss" of a private company. — [Kanzlei Plutte](https://www.ra-plutte.de/olg-hamburg-erlaubt-fotonutzung-fuer-ki-training/amp/); [Ferner Alsdorf](https://www.ferner-alsdorf.de/ki-training-und-urheberrecht-zulaessigkeit-des-webscrapings-fuer-trainingsdatensaetze-olg-hh/)
- OLG Hamburg held the download lawful under both §44b and §60d. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt); [CMS](https://cms.law/de/deu/legal-updates/vervielfaeltigung-eines-fotos-fuer-erstellung-eines-ki-trainingsdatensatzes-zulaessig)
- LG München I (GEMA v OpenAI, 11.11.2025, 42 O 14139/24): the TDM exception covers only reproductions "in the run-up to automated processes for analysing large data sets". It "does not permit memorisation in the AI language model or regurgitation in the output." — [CMS on GEMA v OpenAI](https://cms.law/en/deu/legal-updates/gema-vs.-openai-urheberrechtliche-grundsatzentscheidung-des-landgerichts-muenchen-i-ergangen)
- OLG Hamburg did not discuss lawful access, retention/deletion duties, or the legality of the later training stage. It focused on dataset creation and verification acts (image-text correlation checks). — [Kanzlei Plutte](https://www.ra-plutte.de/olg-hamburg-erlaubt-fotonutzung-fuer-ki-training/amp/); [Ferner Alsdorf](https://www.ferner-alsdorf.de/ki-training-und-urheberrecht-zulaessigkeit-des-webscrapings-fuer-trainingsdatensaetze-olg-hh/)

### Inferences
- **§60d for this project (Medium-Low confidence that it applies):** the statute does let a private individual qualify as an "individual researcher", so an institution is not required. The hurdle is "non-commercial purposes". The project itself is non-commercial, but its declared aim is models that others can use commercially. OLG Hamburg let LAION keep §60d despite downstream commercial use. LAION, however, is a non-profit research association with a research mission. Whether a lone developer publishing a product-like model zoo is doing "scientific research" (methodical, aimed at knowledge gain, with results verifiable) is untested. Recommendation: rely on §44b as the primary basis and treat §60d at most as a secondary argument. Under §44b, honour opt-outs and delete copies.
- **Retention (§44b(2) sentence 2):** keeping raw snapshots locally "forever" sits uneasily with the deletion duty. A defensible reading is that copies may be kept while still needed for TDM: training, re-training, evaluation, and reproducibility of the published pipeline. This is UNSETTLED. No court has defined how long "erforderlich" lasts, and I found no source on whether reproducibility or audit needs justify retention. Automatable control: give each snapshot a recorded purpose and a review/deletion date, and keep the provenance metadata (hashes, URLs, dates) after deleting content. Metadata are not copies of the works.
- **Lawful access:** content behind logins, paywalls, or with circumvented technical protection is not "lawfully accessible". Publicly reachable pages generally are. ToS that forbid scraping may matter contractually, but under §44b(3) only machine-readable reservations defeat the exception (see Q2). The harness should never fetch behind authentication or bypass rate-limit or anti-bot measures.
- The TDM exception covers copying for analysis. It does not cover memorisation in weights or verbatim output (LG München I, UNSETTLED on appeal). So §44b compliance at fetch time is necessary but not sufficient (see Q4).

### Gaps
- No court decision found on how long §44b(2) allows retention, or whether "reproducibility" counts as a TDM need.
- No decision found on §60d for a private individual or open-source developer.
- No primary source for a "lawful access" definition in German case law. I relied on statutory text plus general understanding. Recital 14 of Directive 2019/790 (which addresses lawful access, including freely available online content) was not fetched in this session.

## Q2: Machine-readable reservation (§44b(3)): what counts; LG/OLG Hamburg LAION; other decisions through Oct 2026

### Takeaway
After OLG Hamburg (10.12.2025), a natural-language reservation in ToS or an imprint was not machine-readable as of 2021. The rightsholder must prove that the form used was machine-readable at the time of use. The court left open whether natural language can ever suffice. robots.txt (RFC 9309), TDMRep (`/.well-known/tdmrep.json`, HTTP headers, meta tags) and HTTP headers are the recognised safe signals. The BGH revision (I ZR 281/25) is pending: hearing 3.9.2026, announced decision date 17.12.2026 (single source). A CJEU referral is possible. Confidence: Medium-High on OLG holding, Low on how the BGH will rule.

### Cited Findings
- OLG Hamburg, 10.12.2025, 5 U 104/24, upheld LG Hamburg 27.09.2024, 310 O 227/23 (Kneschke v LAION). — [CMS](https://cms.law/de/deu/legal-updates/vervielfaeltigung-eines-fotos-fuer-erstellung-eines-ki-trainingsdatensatzes-zulaessig)
- The image agency's reservation "habe ... nicht die gesetzlich vorgesehene Form (Maschinenlesbarkeit) aufgewiesen" at the time of download. — [Kanzlei Plutte](https://www.ra-plutte.de/olg-hamburg-erlaubt-fotonutzung-fuer-ki-training/amp/)
- The Senate left open whether natural language can ever be machine-readable. The form had to be machine-readable at the time of use (second half of 2021), and the court could not assume natural language was a "maschinenlesbare Form" in 2021. A reservation counts as machine-readable only if it can be automatically captured, interpreted and followed. Burden of proof lies with the rightsholder. — [Search summary citing damm-legal / urheber.info / itmr-legal](https://www.damm-legal.de/olg-hamburg-laion-darf-bilder-eines-fotografen-zum-data-mining-aus-einer-oeffentlich-zugaenglichen-datenbank-herunterladen-ki-2025); [urheber.info](https://urheber.info/diskurs/hamburger-olg-urteil-im-fall-laion)
- The rightsholder's evidence from ChatGPT tests in 2023, and from tools without documented 2021 availability, did not suffice. Effectiveness is measured at the moment of use. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt)
- Characterisations differ. One secondary source states flatly that natural-language ToS notices are "legally insufficient" and names robots.txt, HTTP headers and TDMRep as effective. — [blckalpaca / CMS search summary](https://cms.law/de/deu/legal-updates/vervielfaeltigung-eines-fotos-fuer-erstellung-eines-ki-trainingsdatensatzes-zulaessig). Others say the court left the principle open and decided on the 2021 state of the art. — [Ferner Alsdorf](https://www.ferner-alsdorf.de/ki-training-und-urheberrecht-zulaessigkeit-des-webscrapings-fuer-trainingsdatensaetze-olg-hh/); [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt). The "left open" reading is the more specific and better supported one.
- Background (from my knowledge, not re-verified in this session): LG Hamburg 2024 had said obiter that a natural-language reservation could be "maschinenverständlich" given modern NLP, and decided the case on §60d. OLG Hamburg did not adopt this reasoning for 2021. — see [LTO on LG Hamburg](https://www.lto.de/recht/hintergruende/h/kuenstliche-intelligenz-ki-urheberrecht-text-data-mining-lg-hamburg-310o22723) (not fetched)
- Revision to the BGH was admitted; the judgment is not final. — [Kanzlei Plutte](https://www.ra-plutte.de/olg-hamburg-erlaubt-fotonutzung-fuer-ki-training/amp/)
- BGH I ZR 281/25: hearing 3.9.2026; decision announced for 17.12.2026; CJEU referral possible. — [itmr-legal (as of 3.10.2026)](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt). Single source; a direct search did not confirm it. The same source also miscites the OLG judgment as "October 2025", so treat its dates with caution.
- The same source reports an EU Commission feasibility study on a TDM opt-out registry (13.7.2026) and an announced, not yet published, list of recognised opt-out protocols. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt) (unverified elsewhere)
- **TDMRep** is a W3C Community Group Final Report (May 2024), **not a W3C Recommendation**. Properties: `tdm-reservation` (1 = reserved, 0 = not reserved) and `tdm-policy` (URL of an ODRL-based policy). Locations: `/.well-known/tdmrep.json`, HTTP response headers, HTML `<meta>`, EPUB metadata, PDF XMP. More specific levels override earlier ones. Policies can constrain by purpose (`tdm:research` / `tdm:non-research`). — [W3C TDMRep CG report](https://www.w3.org/community/reports/tdmrep/CG-FINAL-tdmrep-20240510/)
- **CJEU C-250/25 Like Company v Google Ireland** (referred 3.4.2025 by Budapest Környéki Törvényszék) asks whether LLM training is reproduction, whether it falls under Art. 4 DSM, whether chatbot output partially identical to press content is communication to the public or reproduction, and related questions on Art. 15 DSM. It is the first CJEU case on generative AI and TDM; I found no ruling or AG opinion as of the search. — [DDG](https://en.ddg.fr/actualite/first-ai-related-reference-to-the-cjeu-preliminary-questions-in-case-c-250-25-like-company-v-google-ireland); [Stephenson Harwood](https://www.stephensonharwood.com/zh/见解/cjeu-to-rule-on-ai-and-copyright-in-a-landmark-case-against-google/)

### Inferences
- **What the harness should treat as an opt-out (conservative policy):**
  - (a) robots.txt disallow for the crawler's user-agent, for `*`, or for known AI-training agents (GPTBot, CCBot, Google-Extended, etc.). Treating AI-specific UA blocks as a reservation against TDM generally is the conservative reading.
  - (b) TDMRep `tdm-reservation: 1` in any of its locations.
  - (c) `noai`/`noimageai` meta or X-Robots-Tag directives.
  - (d) ai.txt or similar non-standard files: treat as a reservation if present. Their legal status is untested, and honouring them costs little.
  - (e) Natural-language ToS or imprint clauses that prohibit TDM or AI training: after 2025, with LLMs widely available, a court may well find them "machine-readable". OLG Hamburg left this open for later dates, and the BGH decision is pending. Treat them as a reservation (Medium confidence that this is required, High that it is prudent).
- Because effectiveness is judged at the time of use, the harness must snapshot all signals at fetch time, not at audit time.
- If the BGH (17.12.2026) or the CJEU rules differently, the policy must be revisited. Calendar a review after 17.12.2026.

### Gaps
- Full text of OLG Hamburg 5 U 104/24 and LG Hamburg 310 O 227/23 not retrieved from primary sources (justiz.hamburg.de / openjur). Holdings above rest on law-firm and blog summaries.
- BGH hearing and decision dates not confirmed on bundesgerichtshof.de.
- No decision found on ai.txt, `noai` meta tags, or AI-specific robots.txt user-agents as a general TDM reservation.
- No source confirmed whether the Commission list of recognised protocols has been published.

## Q3: Per-source compliance documentation; GPAI Code of Practice copyright chapter; applicability to a non-signatory hobby project

### Takeaway
The GPAI Code of Practice copyright chapter (July 2025) sets the de facto benchmark:
- crawlers that obey robots.txt (RFC 9309) and other appropriate machine-readable protocols
- no circumvention of paywalls or technical measures
- exclusion of listed piracy domains
- output safeguards against reproducing training material
- an acceptable-use policy prohibiting infringing uses
- a published copyright policy and crawler information

The AI Act Art. 53(1)(c) copyright-policy duty applies to GPAI model providers even when the model is open-source. Whether a small mobility text model is "GPAI" at all is doubtful (indicative threshold 10^23 FLOP). Adopting the Code's measures voluntarily is cheap and maps well to automation. Confidence: Medium.

### Cited Findings
- Code copyright chapter, five measures. Signatories:
  - use crawlers that read and follow robots.txt per IETF RFC 9309 and subsequent versions
  - identify and comply with other "appropriate" machine-readable protocols (from standardisation bodies or widely adopted state of the art)
  - do not circumvent technical measures such as paywalls
  - exclude piracy domains named on an EU-published list
  - publish crawler info and robots.txt features
  - mitigate infringing outputs through technical safeguards and acceptable-use terms
  — [Slaughter and May](https://thelens.slaughterandmay.com/post/102ktcs/mining-the-copyright-chapter-of-the-gpai-code); [Freshfields](https://technologyquotient.freshfields.com/post/102ksv0/the-final-general-purpose-ai-code-of-practice-a-short-guide); [Code text PDF](https://www.editionmultimedia.fr/wp-content/uploads/2025/07/Code-of-Practice-for-GPAI-Copyright-10-07-25.pdf)
- Commission GPAI guidelines: indicative, rebuttable criterion that models trained with >10^23 FLOP that can generate language are GPAI. Models below that may still be GPAI if sufficiently general. — [artificialintelligenceact.eu](https://artificialintelligenceact.eu/gpai/); [Freshfields](https://technologyquotient.freshfields.com/post/102kxqo/eu-ai-act-unpacked-27-guidelines-on-the-scope-of-obligations-for-general-purpos)
- Open-source GPAI providers are exempt from downstream and authority documentation duties but **must still** have a copyright policy and publish the training-data summary. — [artificialintelligenceact.eu](https://artificialintelligenceact.eu/gpai/); [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/ip-insights/2025/10/copyright-compliance-under-the-eu-ai-act-for-gpai-model-providers.html)
- AI Act enforcement of GPAI obligations began 2.8.2026. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt)
- OLG Hamburg placed the burden on the rightsholder to prove machine-readability at the time of use. The user must still show the exception's prerequisites. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt)

### Inferences
- **Provenance record per fetched document (automatable):**
  - source URL, canonical URL, domain
  - fetch timestamp (UTC)
  - crawler user-agent string used
  - HTTP status and response headers (including X-Robots-Tag, tdm-reservation, tdm-policy)
  - robots.txt raw snapshot plus hash plus evaluated verdict for the UA
  - `/.well-known/tdmrep.json` snapshot plus verdict
  - HTML meta robots/noai/tdm tags
  - ai.txt snapshot if present
  - ToS/imprint URL plus snapshot hash, with a classifier verdict on TDM/AI prohibition and human confirmation flag
  - licence detected (e.g. CC BY, CC BY-NC-ND, OA licence of papers)
  - access mode (public / no login / no paywall)
  - legal basis claimed (§44b / §5 / licence / §60d)
  - content hash
  - retention purpose and review/delete date
  - deletion timestamp
  - inclusion in which training run (dataset version)
- **Domain-level policy file:**
  - allow/deny verdict, reason, reviewer, date
  - piracy blocklist (EU list once published, plus well-known shadow libraries)
- **Per-dataset (Zenodo/UCI/Bitbucket/DTU):**
  - DOI/URL, version, licence string and URL, licence snapshot
  - attribution text
  - redistribution allowed y/n
  - commercial use allowed y/n
  - share-alike y/n
  - whether the derived model is restricted (NC/ND licences)
  - date checked
- Even if the zoo's models fall below GPAI thresholds, publishing a short copyright policy (crawler UA, opt-outs honoured, blocklists, takedown contact) is low-cost and matches the Code. Whether a private non-commercial individual "places on the market" is UNSETTLED. Publishing on Hugging Face for others to use, including commercially, likely counts as making available.

### Gaps
- I did not fetch the Code's exact wording on record-keeping, complaint mechanisms, or the EU piracy-list status.
- No authoritative source on whether a hobbyist's sub-10^23-FLOP domain model is GPAI.

## Q4: Memorisation in weights and outputs; verbatim quotes in model cards, reports and examples; §51 quotation limits

### Takeaway
LG München I (GEMA v OpenAI, 11.11.2025, not final) held that memorisation counts as reproduction (§16 UrhG) if the model can output the work recognisably. Neither TDM exception covers memorisation or verbatim output. For this project, verbatim quotes in model output, reports and model cards are the highest-risk element. Short factual snippets from forum posts or reviews may fall below the originality threshold or within §51, but this must be checked per quote. Confidence: Medium (first-instance ruling, appeal expected).

### Cited Findings
- LG München I, 11.11.2025, 42 O 14139/24: storing works in model parameters is reproduction under §16 UrhG. "It is sufficient that the AI language model is capable of reproducing the content in a recognisable form." That the content exists only as probability values is irrelevant. — [CMS](https://cms.law/en/deu/legal-updates/gema-vs.-openai-urheberrechtliche-grundsatzentscheidung-des-landgerichts-muenchen-i-ergangen)
- Regurgitation in outputs was held to infringe reproduction (§16), adaptation (§23) and making available (§19a). Even "simple prompts" suffice; hallucinated additions do not make the original unrecognisable. — [CMS](https://cms.law/en/deu/legal-updates/gema-vs.-openai-urheberrechtliche-grundsatzentscheidung-des-landgerichts-muenchen-i-ergangen)
- The ruling did not address quotation or other exceptions. It is not final, OpenAI announced an appeal, and I found no OLG München decision in 2026 searches. — [CMS](https://cms.law/en/deu/legal-updates/gema-vs.-openai-urheberrechtliche-grundsatzentscheidung-des-landgerichts-muenchen-i-ergangen); [Fieldfisher](https://www.fieldfisher.com/de-de/locations/germany/insights/gema-vs-openai-zum-urteil-und-seiner-bedeutung)
- The works were song lyrics (short, highly original texts). — [WBS](https://www.wbs.legal/urheberrecht/gema-gewinnt-gegen-openai-chatgpt-verletzt-urheberrechte-von-songwritern-84612/)
- CJEU C-250/25 will address whether LLM output partially identical to source text is reproduction or communication to the public. — [DDG](https://en.ddg.fr/actualite/first-ai-related-reference-to-the-cjeu-preliminary-questions-in-case-c-250-25-like-company-v-google-ireland)
- The GPAI Code asks for technical safeguards against outputs reproducing training material. — [Freshfields](https://technologyquotient.freshfields.com/post/102ksv0/the-final-general-purpose-ai-code-of-practice-a-short-guide)

### Inferences
- **Model output format with verbatim quotes:**
  - If the model is designed to emit verbatim quotes from training texts, it is designed to regurgitate. Under GEMA v OpenAI's logic, both the weights (if they reproduce recognisable works) and the outputs could be infringing reproductions.
  - Lower-risk design: quotes come from the user-supplied input at inference time (extractive quoting of the input document), not from memorised training data. Then the model itself does not hold the work. The user's own use of the input text is outside the project's responsibility, or within §51 if used for analysis.
  - The harness should test this: run a memorisation/extraction probe (prompt with training-document prefixes and measure verbatim n-gram overlap, e.g. ≥50 chars or ≥8-gram runs). Gate release on a threshold.
- **Model cards / reports / examples:**
  - Fictional examples carry no third-party copyright risk. Verify automatically that examples do not contain n-gram overlaps with the raw corpus.
  - Evaluation reports that quote real forum posts or reviews: §51 UrhG requires a quotation purpose (engagement with the quoted text), only the extent the purpose requires, an unchanged quote (§62), and source attribution (§63). Mass illustrative quoting without discussion does not qualify. Statutory requirements are from my knowledge of §§51, 62, 63 UrhG: [§51](https://www.gesetze-im-internet.de/urhg/__51.html) (not fetched this session).
  - Short everyday forum/review sentences may lack originality (Schöpfungshöhe), but that is case-by-case. Personal data and GDPR issues of quoting forum users are out of scope here but relevant.
- Practical rule for automation: no verbatim span from raw snapshots over N characters in any published artifact (cards, reports, examples, eval files), unless the source is §5 official text or carries a compatible licence (CC BY with attribution). This needs a human decision on N, e.g. 50-100 characters.

### Gaps
- No appeal decision found in GEMA v OpenAI. No German case found on short forum/review texts or on extractive-quote models.
- No authoritative threshold for "recognisable reproduction" in weights.

## Q5: Sui generis database right (§87a ff UrhG, Directive 96/9/EC)

### Takeaway
Scraping a substantial part of a protected database (forum, review platform, paper repository, dataset portal) is "extraction" under §87b. The TDM exception extends to database rights via §87c(1). Opt-outs and lawful access still apply, so TDM-compliant scraping for training is covered. **Republishing** substantial parts, for example in a Hugging Face compendium that mirrors data rather than linking it, is not covered by the TDM exceptions. Confidence: Medium-High.

### Cited Findings
- §87c(1) permits reproduction of a substantial part of a database for, among others, scientific research and text and data mining. §87c(5) requires source attribution per §63. — [§87c UrhG](https://www.gesetze-im-internet.de/urhg/__87c.html)
- §87b(1) sentence 2: repeated and systematic reproduction, distribution or public communication of **insubstantial** parts is also infringing if it conflicts with normal exploitation or unreasonably prejudices the maker's legitimate interests. — [search summary of lxgesetze §87b/e](https://lxgesetze.de/urhg/87e); statutory text at [gesetze-im-internet §87b](https://www.gesetze-im-internet.de/urhg/__87b.html) (not fetched)
- CJEU C-762/19 CV-Online Latvia v Melons (3.6.2021): transferring substantial contents of a database and making them available to the public without consent is extraction and re-utilisation under Art. 7(1) Dir. 96/9 if it deprives the maker of income that recoups the investment. Following AG Szpunar, infringement requires an adverse effect on the investment. — [Clifford Chance](https://cliffordchance.com/expertise/services/intellectual-property/global-ip-updates/2021/q4/cv-online-latvia-v-melons.html); [SCL](https://www.scl.org/12290-cjeu-search-engine-copying-of-databases-infringes-sui-generis-right-where-it-adversely-affects-database-maker-investment/); [IPPT judgment](https://www.ippt.eu/sites/ippt/files/2021/IPPT20210603_CJEU_CV-Online_Latvia_v_Melons.pdf)
- Where a database is not protected by sui generis right, the CJEU (Ryanair, as summarised) allows contractual restrictions on use. ToS can then bind. — [Osborne Clarke](https://www.osborneclarke.com/de/insights/besser-keinen-gesetzlichen-datenbankschutz-eugh-lasst-vertragliche-beschrankungen-von-datenbanknutzung-zu-wenn-die-datenbank-nicht-gesetzlich-geschutzt-ist)

### Inferences
- Scraping forums or review sites for training under §44b/§87c: permissible if opt-out signals are honoured and access is lawful. Avoid systematic full-site mirroring beyond what training needs.
- Publishing derived datasets: never publish raw scraped text or substantial extracts (consistent with the existing project rule). Published statistics, labels, or embeddings that do not reproduce content are low risk.
- **HF compendium of third-party datasets:**
  - A curated list with metadata, links and licence info (no re-hosting) is low risk.
  - Re-hosting files requires the source licence to permit redistribution. CC BY / CC0 / ODbL do, with attribution and share-alike where applicable. "Research only", NC or ND licences, or unspecified terms do not.
  - Collecting many datasets' descriptions verbatim could raise copyright and §87b issues. Write descriptions in your own words.
- Contract (ToS) restrictions may bind independently of copyright where no sui generis right exists (Ryanair). Whether a no-login scraper "accepts" browse-wrap ToS under German law is doubtful but not zero risk (Low confidence).

### Gaps
- No German decision found specifically on AI-training scraping under §87b/§87c.
- Licence terms of the specific Zenodo/UCI/Bitbucket/DTU datasets were not checked (out of scope; per-dataset task).

## Q6: Parliamentary records and official works (§5 UrhG)

### Takeaway
Bundestag plenary minutes (Plenarprotokolle) are generally treated as official works that may be reproduced unchanged with attribution. Laws and decisions are fully free under §5(1). Other "official works" under §5(2) carry an alteration ban (§62) and a source-citation duty (§63). Third-party contributions embedded in reports (e.g. commissioned expert studies, annexed documents) and Landtag or other parliaments' terms need a per-source check. Confidence: Medium.

### Cited Findings
- Plenarprotokolle of the German Bundestag can be reproduced without modification with the source credited, per §5(2) UrhG. — [search summary, Internet Archive record of Bundestag plenary protocol](https://archive.org/details/ger-bt-plenary-13-41/page/n9/mode/2up) (secondary, notice on the document itself)
- §5 UrhG text (my knowledge, not fetched this session): (1) laws, ordinances, official decrees and notices, decisions and official headnotes enjoy no copyright protection. (2) The same applies to other official works published in the official interest for general information, subject to §62(1)-(3) and §63(1),(2) (no alteration, citation of source). — [§5 UrhG](https://www.gesetze-im-internet.de/urhg/__5.html)

### Inferences
- Treat parliamentary records as `legal_basis = §5` with automatic attribution. Avoid altered quotations, or mark alterations. This is the lowest-risk text source and suits verbatim quoting in examples and reports.
- Do not extend §5 automatically to Bundestag "Ausarbeitungen" of the Wissenschaftliche Dienste, agency reports, or commissioned studies. Their status varies, and some carry explicit copyright notices. Classify per document series (a human decision, made once per series).
- Database right in a parliament's documentation system (DIP) is a separate question. §5 covers the works, not necessarily the database investment. The Bundestag offers an open API/open data terms. I did not verify those terms here.

### Gaps
- No primary source fetched for the Bundestag's or Landtage's current open-data licence terms.
- No court decision found on §5 status of Plenarprotokolle (status rests on the notice and general commentary).

## Q7: Scientific papers: open-access licences vs publisher terms prohibiting TDM

### Takeaway
For papers, the licence attached to the specific version fetched governs redistribution and quoting, while §44b governs mere TDM copying. Publisher pages often carry TDMRep or robots signals and ToS reserving TDM. Under the conservative policy in Q2, those are opt-outs. CC BY papers (e.g. on arXiv or PMC OA) are safe to mine and quote with attribution. CC BY-NC/ND papers are fine for TDM under §44b, but their verbatim text must not appear in commercially usable outputs. Confidence: Medium.

### Cited Findings
- TDMRep was designed for, and is used by, publishers. It is expressed via `/.well-known/tdmrep.json`, HTTP headers, HTML meta, EPUB and PDF XMP, with optional `tdm:research` / `tdm:non-research` policy constraints. — [W3C TDMRep](https://www.w3.org/community/reports/tdmrep/CG-FINAL-tdmrep-20240510/)
- §44b(3) only recognises machine-readable reservations for online works. — [§44b UrhG](https://www.gesetze-im-internet.de/urhg/__44b.html)
- Natural-language ToS reservations were insufficient for 2021 (OLG Hamburg), but the question is open for later dates. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt)

### Inferences
- Harness checks for papers:
  - fetch PDF XMP and HTML meta for TDMRep
  - read the licence from the landing page / Crossref metadata (`license` field)
  - prefer OA repositories with explicit CC licences
  - flag publisher domains with `tdm-reservation: 1` and route them to exclusion or a human licensing decision
- Where TDMRep `tdm-policy` says research-only, the project's §60d position is weak (Q1). Treat this as reserved.
- Bypassing publisher paywalls, including through shadow libraries, defeats "lawful access" and matches the Code's piracy exclusion. Hard-block it.

### Gaps
- Specific publishers' (Elsevier, Springer Nature, Wiley) current TDM terms and TDMRep deployment not fetched.
- Crossref licence metadata behaviour not verified in this session.

## Q8: What to automate vs what needs human decisions

### Takeaway
Fetch-time signal capture, rule evaluation, provenance logging, retention timers, blocklists, licence parsing, memorisation and overlap tests, and attribution generation can all be automated. Humans must decide on: legal-basis choice (§44b vs §60d), interpretation of natural-language ToS, ambiguous licences, quote-length thresholds, §5 classification of document series, compendium re-hosting, and re-assessment after the BGH (17.12.2026) and CJEU C-250/25 rulings. Confidence: Medium-High.

### Cited Findings
- Effectiveness of a reservation is assessed at the moment of use, so evidence must be captured contemporaneously. — [itmr-legal](https://itmr-legal.de/blog/ki-training-widersprechen-tdm-vorbehalt)
- The Code expects robots.txt (RFC 9309) compliance, other appropriate protocols, piracy-domain exclusion, no circumvention, output safeguards, and published crawler info. — [Slaughter and May](https://thelens.slaughterandmay.com/post/102ktcs/mining-the-copyright-chapter-of-the-gpai-code)
- Memorisation and regurgitation fall outside TDM (LG München I, not final). — [CMS](https://cms.law/en/deu/legal-updates/gema-vs.-openai-urheberrechtliche-grundsatzentscheidung-des-landgerichts-muenchen-i-ergangen)

### Inferences
**Automate (harness checks, fail-closed):**
1. Fetch gate:
   - robots.txt (RFC 9309) for the project UA and `*`
   - AI-specific UA blocks treated as a reservation
   - `/.well-known/tdmrep.json`, `tdm-reservation` HTTP header, meta tags
   - X-Robots-Tag / meta `noai`, `noimageai`
   - ai.txt
   - no auth, no paywall, no CAPTCHA bypass
   - piracy/shadow-library domain blocklist
   - per-domain manual denylist
   - any reservation means skip and log
2. ToS screen: fetch ToS/imprint, run a keyword/LLM classifier for TDM/AI/scraping prohibitions, route hits to human review. Default to exclusion pending review.
3. Provenance record per document (fields in Q3), stored with the local snapshot and kept after content deletion.
4. Retention: each snapshot has a purpose and a review date. The harness flags snapshots not used in any active training/eval run for longer than X months for deletion (§44b(2) s.2). Log the deletion.
5. Re-check: before each new training run, re-evaluate opt-outs for all domains. The conservative choice is to drop newly opted-out sources from future runs. The law measures at time of use, and each new training copy is a new use.
6. Dataset licence check for Zenodo/UCI/Bitbucket/DTU:
   - parse the SPDX/licence string
   - block NC/ND/"research-only"/unknown for models declared commercially usable
   - auto-generate the attribution file
7. Publication gate:
   - n-gram/char-span overlap of every published artifact (model card, examples, eval reports, HF compendium descriptions) against the raw corpus
   - memorisation probe on released weights (prefix-completion extraction rate)
   - fail above threshold unless the source is §5 or CC BY with attribution present
8. Compendium: links plus metadata only by default. Re-hosting only if the licence permits redistribution, with attribution and share-alike recorded.
9. Publish a copyright policy file (crawler UA, signals honoured, blocklists, takedown contact), mirroring the Code.

**Human decisions (owner):**
- Primary legal basis: §44b only (recommended), or additionally claim §60d.
- Treat natural-language ToS reservations as binding (recommended: yes) and resolve flagged ToS hits.
- Thresholds: max verbatim span length in published artifacts, memorisation-probe pass threshold, retention period.
- §5 classification per document series (Plenarprotokolle yes; reports and studies per series).
- Whether output-format verbatim quotes may come only from the inference-time input (recommended) or also from training memory.
- Re-hosting vs linking in the HF compendium; handling of NC/ND datasets.
- Re-assessment triggers: BGH I ZR 281/25 (announced 17.12.2026), OLG München appeal in GEMA v OpenAI, CJEU C-250/25, and the Commission protocol list and opt-out registry.
- Handling of takedown/opt-out requests received after publication (re-training vs ignore for already-trained models), which is UNSETTLED law.

### Gaps
- No source found on whether a later opt-out obliges retraining or deleting an already trained model.
- No legal standard for acceptable memorisation rates. Thresholds are engineering choices.
