# GDPR (DSGVO) and BDSG obligations for a private, public, non-commercial ML model zoo (Germany)

Status: research notes, current as of 2026-10-08. Not legal advice. Confidence tags: [High] = statute text or CJEU/EDPB position confirmed in sources; [Medium] = well-supported reading but not decided for this fact pattern; [Low] = unsettled or extrapolated. Constraint: the EDPB website (edpb.europa.eu) was not reachable from the research environment (DNS failure), so EDPB Opinion 28/2024 content comes from reputable secondary summaries and should be checked against the PDF before it is quoted verbatim.

Primary legal texts used throughout: [GDPR, EUR-Lex CELEX 32016R0679](https://eur-lex.europa.eu/eli/reg/2016/679/oj); [BDSG, gesetze-im-internet.de](https://www.gesetze-im-internet.de/bdsg_2018/).

## 1. Does the household exemption (Art. 2(2)(c) GDPR) apply?

### Takeaway
No, not for the publishing part, and very probably not for the scraping and training pipeline either. CJEU case law reads the exemption narrowly. Disclosure on the internet to an indefinite number of people takes an activity outside it, and the project's stated purpose is a public model zoo. Treat the owner as a full GDPR controller, and as a "nicht-öffentliche Stelle" under the BDSG. [High]

### Cited Findings
- Lindqvist (C-101/01, 6 Nov 2003): the exemption for purely personal or household activities does not apply where data are published on the internet and so made accessible to an indefinite number of people. The facts involved a private lay preacher's website about parishioners. — [Thomas Helbing GDPR hub, Lindqvist](https://www.thomashelbing.com/en/wissen/dsgvo-hub/rechtsprechung/1.4.43-eugh-lindqvist)
- Ryneš (C-212/13, 11 Dec 2014): a private home CCTV camera that also covers public space is not "purely" personal or household activity. The exemption is interpreted strictly. — [Hunton, CJEU adopts strict approach](https://www.hunton.com/privacy-and-cybersecurity-law-blog/cjeu-adopts-strict-approach-use-cctv); [Hogan Lovells](https://www.hoganlovells.com/en/publications/cctv-cjeu-narrows-the-scope-of-the-household-exemption)
- Jehovan todistajat (C-25/17, 10 July 2018) confirmed the same line for notes taken during door-to-door preaching, i.e. activity aimed outside the private sphere. — [JIPITEC article on the household exemption](https://jde.pubsys.hbz-nrw.de/index.php/jipitec/article/view/683)
- Art. 2(2)(c) GDPR covers processing "by a natural person in the course of a purely personal or household activity". Recital 18 adds that this means "no connection to a professional or commercial activity". — [GDPR, EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- The BDSG applies to non-public bodies (which includes natural persons) unless the processing is for exclusively personal or family activities (§ 1(1) sentence 2 BDSG). — [BDSG § 1](https://www.gesetze-im-internet.de/bdsg_2018/__1.html)

### Inferences
- Non-commercial status does not help. The deciding factor is the public, indefinite audience of the weights, model card, examples and any dataset compendium (Lindqvist). [High]
- Upstream steps (scraping, snapshot storage, LLM labeling, training) are done for a public release and send data to third parties (OpenRouter, Anthropic). They are therefore not "purely" personal either (Ryneš, Jehovan todistajat). [Medium-High]
- A possible counter-argument: a private hobby project on the owner's own machine. This collapses once results are published or data goes to third-party APIs. Do not rely on it. [Medium]
- **Harness:** none. This is a fixed legal premise, recorded once in the compliance docs. **Human decision:** confirm the project accepts controller status, and who the named contact is (name and address are needed for Art. 13/14 notices; see § 4).

### Gaps
- No CJEU ruling yet on a private individual who trains and publishes ML models. Buivids (C-345/17, 2019, a private person posting a video on YouTube) is reportedly on point, but its text was not verified in this session.

## 2. Legal basis for scraping and training; model anonymity; consequences of unlawful training

### Takeaway
The realistic legal basis is Art. 6(1)(f) legitimate interest, and it must be shown through the three-step test in EDPB Opinion 28/2024 (17 Dec 2024). Under that opinion a model is anonymous only if extraction or regurgitation of training-data personal data is negligible, judged case by case and with documented evidence. Unlawful development can lead to dataset erasure or retraining orders, and can affect the lawfulness of deployment unless the model is proven anonymous. The Digital Omnibus proposal for a statutory AI legitimate interest (Art. 88c, now "88bis" in the Council draft) is not law as of 2026-10. [High on the current position; Low on the future direction]

### Cited Findings
- EDPB Opinion 28/2024 (adopted 17 Dec 2024 under Art. 64(2) at the Irish DPC's request) covers three things: when AI models are anonymous, how to show legitimate interest, and how unlawful processing during development affects later use. — [CMS summary](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models); [Matheson](https://www.matheson.com/insights/edpb-publishes-eagerly-anticipated-opinion-on-ai-models/)
- Anonymity test: the likelihood of directly or probabilistically extracting training-data personal data must be "negligible", and the risk of obtaining such data through queries, even unintentionally, must be "insignificant". The assessment follows Recital 26 ("means reasonably likely to be used" by the controller *or any other party*) and must account for unintended reuse or disclosure of the model. — [CMS](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models)
- Legitimate interest is not a "by default" legal basis. The controller must show the three steps (legitimate interest, necessity, balancing), and the reasonable expectations of data subjects carry great weight. Mitigations named include pseudonymisation, synthetic data, transparency beyond Arts. 13/14 (e.g. collection criteria and the datasets used), and an opt-out "from the outset". — [CMS](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models)
- Consequences of breaching Arts. 5/6 during development: fines, temporary limits on processing, partial or full erasure of datasets, and retraining orders. The opinion does not allocate duties across the AI value chain. — [CMS](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models)
- CNIL practical guides (19 June 2025) confirm that web scraping for AI training can rest on legitimate interest under strict safeguards: respect robots.txt and ai.txt, exclude sensitive data and data about minors from collection, and run a DPIA where risks are high. — [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/06/web-scraping-for-ai-development--the-cnil-builds-on-edpb-guidanc.html); [Hogan Lovells](https://www.hoganlovells.com/fr/publications/development-of-an-ai-system-cnil-issues-guidelines-regarding-collection-of-data-via-web-scraping)
- EDPB Guidelines 01/2025 on pseudonymisation were adopted on 16 Jan 2025 (consultation until 28 Feb 2025). Pseudonymised data stays personal data for the party able to re-identify. — [EDPB Guidelines 01/2025 PDF](https://www.edpb.europa.eu/system/files/2025-01/edpb_guidelines_202501_pseudonymisation_en.pdf); [Hunton](https://www.hunton.com/insights/publications/edpb-advises-on-pseudonymisation-for-gdpr-compliance). One secondary source mentions separate EDPB anonymisation guidelines ("04/2025"). This was not verified. — [European Law Blog](https://www.europeanlawblog.eu/pub/tfef074h)
- CJEU EDPS v SRB (C-413/23 P, 4 Sept 2025): pseudonymised data can be non-personal for a *recipient* who cannot re-identify with means reasonably likely to be used, but stays personal for the original controller. Opinions in comments "relate to" their authors. Transparency is judged from the controller's viewpoint at the time of collection. — [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/09/pseudonymized-data-after-edps-v-srb.html); [Bird & Bird](https://cm.twobirds.com/en/insights/2025/eu-the-srb-decision-a-new-era-for-personal-data-and-data-processing-agreements); [datenschutz-notizen](https://www.datenschutz-notizen.de/pseudonymised-data-not-always-personal-according-to-the-latest-cjeu-judgement-1555813/)
- Digital Omnibus: the Commission's proposal adds Art. 88c GDPR, making AI development and operation a legitimate interest unless law requires consent. A balancing test, safeguards and an *unconditional* right to object still apply. — [Taylor Wessing](https://www.taylorwessing.com/en/global-data-hub/2026/the-digital-omnibus-proposal/gdh----the-digital-omnibus-and-gdpr). The EDPB/EDPS joint opinion of 11 Feb 2026 rejected narrowing the definition of personal data and said Art. 88c is unclear and leaves the three-step test in place. — [noyb](https://noyb.eu/en/digital-omnibus-eu-dpas-reject-many-proposed-changes-gdpr). As of Sept 2026 a leaked Council (Irish Presidency) draft renames it Art. 88bis. There is no Council general approach yet, and Parliament and trilogue are still ahead. — [Resultsense, 21 Sept 2026](https://www.resultsense.com/news/2026-09-21-noyb-gdpr-article-88bis-ai/)

### Inferences
- Three-step test as it might be drafted for scout-large [Medium]:
  1. *Interest:* research and open publication of a mobility-domain JTBD extractor. This is lawful, specific and present, and freedom of science/information (Art. 13 CFR) supports it.
  2. *Necessity:* real user language about mobility pains and gains is hard to replace fully with synthetic text. However, usernames, e-mail addresses, phone numbers, handles and other direct identifiers are *not* needed. This supports redaction before labeling and favours sources with low personal content (reports, papers, parliamentary records) over forums.
  3. *Balancing:* public forum posts carry moderate reasonable expectations of being read, and low expectations of being sent to US LLM providers and turned into a published model. Mitigations tip the balance: redaction, excluding sensitive sub-forums, honouring robots.txt and ai.txt, no publication of the raw corpus, an opt-out and objection channel, and a memorisation test before each release.
- Is a token-classifier model "anonymous"? scout-large is an encoder (XLM-R) token classifier. It outputs labels or spans *over the input text*, not free generation, so extraction by querying is structurally much harder than with generative LLMs. Probabilistic attacks such as membership inference on the weights remain possible in theory. Claiming anonymity is defensible only with documented tests. [Medium-Low; EDPB has not addressed encoder classifiers specifically]
- The SRB "relative approach" helps on the *recipient* side (e.g. Hugging Face downloaders may hold only non-personal weights). It does not relieve the owner, who keeps raw snapshots and therefore holds personal data. [Medium]
- The HmbBfDI thesis (LLMs do not store personal data) is effectively superseded at EU level by Opinion 28/2024's case-by-case approach (see § 8). Do not rely on it alone.
- **Harness checks:**
  - Every source in the source registry has a documented legal-basis record (LIA reference ID).
  - robots.txt and ai.txt/TDM-reservation status was captured at fetch time and respected.
  - A blocked-domain and opt-out list is applied before fetching.
  - A redaction pass ran on 100% of snapshots before any labeling call (counters, regex/NER residual scan).
  - Memorisation tests ran on each release candidate (canary or PII probe, membership-inference score).
  - The model card contains the transparency section.
- **Human decisions:**
  - Writing and approving the Legitimate Interest Assessment (LIA) per source class.
  - Accepting residual risk.
  - Deciding whether to claim "model is anonymous" (I recommend not claiming it; say "measures taken to minimise personal data" instead).

### Gaps
- The verbatim EDPB Opinion 28/2024 paragraphs (e.g. the list of scraping mitigations and the three deployment scenarios) could not be fetched because the EDPB site was unreachable. Verify against the [EDPB PDF](https://www.edpb.europa.eu/system/files/2024-12/edpb_opinion_202428_ai-models_en.pdf).
- No EDPB guidance found that is specific to small or non-commercial open-weight releases.
- The status of final EDPB anonymisation guidelines (if any) for 2025–2026 was not confirmed.

## 3. Special categories (Art. 9) in forum texts; "manifestly made public"

### Takeaway
Forum texts will contain Art. 9 data (health, religion, political opinion, sex life, trade-union membership), as well as Art. 10 data (criminal offences). Art. 9(2)(e) needs a clear, deliberate act by the *data subject* to make that data public. It does not cover data about third parties, and it is unreliable for scraped forums. The safest course is to exclude or redact special-category content before labeling and training, and to document this. [Medium-High]

### Cited Findings
- Meta v Bundeskartellamt (C-252/21, 4 July 2023): sensitive data generated by merely visiting websites or apps is not "manifestly made public" by the user. The exception requires the data subject to have *intended*, explicitly and by a clear affirmative act, to make the data accessible to the general public (the Court refers to e.g. account settings that make data public). — [DLA Piper](https://privacymatters.dlapiper.com/2023/07/eu-cjeus-landmark-decision-in-meta-vs-bundeskartellamt/); [Thomas Helbing GDPR hub](https://www.thomashelbing.com/en/wissen/dsgvo-hub/rechtsprechung/1.4.16-eugh-meta-bundeskartellamt)
- Art. 9(1) prohibits processing special categories unless an Art. 9(2) exception applies. Art. 9(2)(j) together with § 27 BDSG allows processing for scientific research purposes where necessary, where the controller's interests substantially outweigh those of the data subject, and with safeguards (§ 22(2) BDSG measures). — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj); [BDSG § 27](https://www.gesetze-im-internet.de/bdsg_2018/__27.html); [BDSG § 22](https://www.gesetze-im-internet.de/bdsg_2018/__22.html)
- CNIL (June 2025) recommends excluding sensitive data from collection during scraping. — [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/06/web-scraping-for-ai-development--the-cnil-builds-on-edpb-guidanc.html)

### Inferences
- Art. 9(2)(e) might cover a self-disclosure in an *open* forum (no login) by the author about themselves, but never mentions of third parties. It also does not hold where the author used a pseudonym expecting a community audience. Per-post verification is impossible at scale, so 9(2)(e) is not a reliable basis. [Medium]
- Whether § 27 BDSG "research" covers a private individual is unsettled. Publishing results supports it; the lack of an institution and of ethics review weakens it. [Low-Medium]
- The model's purpose (jobs, pains, gains about mobility) does not *need* health or religion content. Data minimisation therefore argues for filtering it out (e.g. excluding health sub-forums, plus a sensitive-topic classifier before labeling). The CJEU line in Lindenapotheke (C-21/23) treats data from which sensitive information *can be inferred* as Art. 9 data. That case was not checked in this session.
- **Harness checks:**
  - Source allowlist and denylist (no health, religion, dating or political-party sub-forums).
  - Every snapshot passes through a sensitive-category classifier or keyword flag with a set threshold; flagged items are quarantined from labeling.
  - Model-card example texts contain no Art. 9 content.
- **Human decisions:**
  - The quarantine threshold.
  - Whether some flagged content is kept (e.g. mobility-related disability or accessibility pains are both health data and highly relevant). This needs an explicit decision and documented justification under Art. 9(2)(j)/§ 27 BDSG, or exclusion.

### Gaps
- No German DPA statement found on Art. 9 for scraped training corpora specifically.
- Lindenapotheke and the CJEU's 2024–2025 case law on inferred sensitive data were not verified here.

## 4. Information duties: Art. 14 and the Art. 14(5)(b) exemption

### Takeaway
Art. 14 applies, because the data is not collected from the data subjects. Individual notification of forum authors will usually be disproportionate under Art. 14(5)(b). The exemption, however, *requires* "appropriate measures … including making the information publicly available". So a public privacy notice for training data is mandatory in practice, and the EDPB asks for transparency beyond Arts. 13/14. [High]

### Cited Findings
- Art. 14(5)(b) GDPR: no individual notice is needed where it is impossible or would involve disproportionate effort, "in particular for processing for … scientific or historical research purposes or statistical purposes", but "the controller shall take appropriate measures to protect the data subject's rights … including making the information publicly available". — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- EDPB Opinion 28/2024 lists enhanced transparency beyond Arts. 13/14 as a mitigating factor in the balancing test (e.g. publishing collection criteria and the datasets used). — [CMS](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models)
- SRB (C-413/23 P): Art. 13/14 transparency, including recipients, is judged from the controller's view at the time of collection. Recipients such as LLM API providers must therefore be named. — [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/09/pseudonymized-data-after-edps-v-srb.html)

### Inferences
- Content of a "Training data privacy notice", following the Art. 14(1)-(2) list [High on the list, Medium on the format]:
  - Controller identity and contact (a private person's address is a practical issue; a c/o or contact address may be needed, as also required under the German DDG Impressum if the site is "geschäftsmäßig").
  - Purposes and legal basis (Art. 6(1)(f), the interest pursued).
  - Categories of data (public posts; usernames removed).
  - Source categories and the list of source domains (Art. 14(2)(f)).
  - Recipients (Anthropic, OpenRouter and its upstream model providers, Hugging Face as host).
  - Third-country transfers and safeguards.
  - Retention per stage.
  - Rights including Art. 21 objection, with the right to object stated *separately and clearly* (Art. 21(4)).
  - Right to complain to a supervisory authority (for a private person in Germany: the Land DPA of residence).
  - That no automated decisions are made about data subjects.
- Placement: a dedicated PRIVACY.md / page in the repo, linked from every model card and the HF org card. The model card itself only needs a short section with the link.
- **Harness checks:**
  - The notice file exists.
  - Every model card links it.
  - The notice lists every source domain in the registry and every LLM provider actually used in the labeling logs (diff check).
  - The retention periods in the notice match the configured deletion jobs.
- **Human decisions:**
  - Controller contact details (privacy and Impressum trade-off).
  - Wording of the balancing summary.

### Gaps
- The DSK/EDPB position on the minimum content of 14(5)(b) public notices for scraping was not retrieved verbatim.
- CJEU Másdi (C-169/23, 2024) on Art. 14(5)(c) was not checked.

## 5. Data subject rights for snapshots and trained weights

### Takeaway
Rights fully apply to raw snapshots and labeled data. For weights, they apply only if the model is not anonymous. Art. 21 objection under legitimate interest must be honoured unless compelling grounds exist, and EDPB/CNIL favour an easy opt-out, ideally an unconditional one. A practical process is: search by URL or quote, delete from the store, add to the exclusion list, and record that the next training run excludes the data. Retraining immediately is not needed unless memorisation is shown. [Medium]

### Cited Findings
- EDPB Opinion 28/2024 names an opt-out "from the outset" and unconditional or easier exercise of rights as mitigating measures. Remedies for unlawful development include erasure of datasets and retraining. — [CMS](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models)
- The DSK TOM guidance for AI systems (June 2025) covers "intervenability", including deletability of training data, across the lifecycle. Collection by scraping is expressly *out of scope* of that paper. — [DSK OH KI-Systeme, Berlin DPA mirror](https://www.datenschutz-berlin.de/fileadmin/user_upload/pdf/publikationen/DSK/2025/20250617-DSK-OH_KI-Systeme.pdf); [Uni Bonn ZMDT summary](https://www.jura.uni-bonn.de/de/forschung-und-lehre/interdisziplinaere-zentren/zmdt/neuigkeiten/dsk-orientierungshilfe)
- The Digital Omnibus proposal would add an *unconditional* right to object for AI legitimate-interest processing. This is not law yet. — [Taylor Wessing](https://www.taylorwessing.com/en/global-data-hub/2026/the-digital-omnibus-proposal/gdh----the-digital-omnibus-and-gdpr)
- Art. 11 GDPR: if the controller cannot identify the data subject (e.g. after redaction of usernames), Arts. 15–20 do not apply unless the data subject provides extra information enabling identification. — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)

### Inferences
- Redaction before storage of the *working* copy strengthens the Art. 11 position. The raw snapshot still contains usernames, so raw snapshots remain fully searchable personal data until deleted. Shortening raw-snapshot retention is the main lever. [Medium]
- Process (target response time one month, Art. 12(3)):
  1. Intake address in the privacy notice.
  2. Identify by URL, username or quote.
  3. Search raw snapshots, redacted corpus, label files and eval sets.
  4. Delete, and add a URL/author hash to a permanent suppression list (hash only, to minimise).
  5. Run a memorisation probe on the current model with the requester's text.
  6. Reply, and log the request in a rights register.
- **Harness checks:**
  - The suppression list is applied in fetch, label and train (zero hits).
  - Searchability: a test that a given URL can be found across all stores via a provenance index.
  - Every training example has provenance (source URL, snapshot ID, hash).
  - Rights-register deadlines are tracked.
- **Human decisions:**
  - Whether "compelling legitimate grounds" outweigh an objection (I recommend always granting it).
  - Whether retraining or re-publishing weights is needed after a confirmed memorisation hit.

### Gaps
- No authoritative guidance found on erasure duties for weights already downloaded by third parties from Hugging Face. Most likely only future releases plus a deprecation notice are feasible.

## 6. Minimisation, redaction, retention; LLM APIs (processor vs. controller); transfers

### Takeaway
Redacting before labeling is a strong Art. 5(1)(c)/Art. 25 control, but free-text bodies still contain names, places and life details, so redacted text usually stays personal data. Whether the LLM providers are processors depends on the contract. Anthropic *consumer* plans (Free/Pro/Max, including Claude Code under a subscription) have used chats for training by default since 28 Sept 2025 unless the user opts out, with up to 5-year retention. Anthropic then acts as an independent controller, which is hard to justify for third-party data. API or commercial terms with a DPA are the processor route. US transfers can rely on the EU-US DPF, upheld by the General Court in Latombe (T-553/23, 3 Sept 2025), where the recipient is certified. [Medium-High]

### Cited Findings
- Anthropic consumer terms update: from 28 Sept 2025, Claude Free, Pro and Max users (including Claude Code) have chats and coding sessions used for training unless they opt out, with retention up to five years (previously 30 days). API, Claude for Work, Gov and Education are not affected. — [Anthropic, Updates to our consumer terms](https://www.anthropic.com/news/updates-to-our-consumer-terms); [Business Today](https://www.businesstoday.in/amp/technology/news/story/anthropic-to-use-claude-conversations-for-ai-training-unless-users-opt-out-by-september-28-491530-2025-08-29)
- General Court, Latombe v Commission (T-553/23, 3 Sept 2025), dismissed the annulment action against the 2023 DPF adequacy decision and found the DPRC sufficiently independent. An appeal was possible within two months. — [Lewis Silkin](https://www.lewissilkin.com/en/insights/2025/09/03/transatlantic-trouble-not-this-time-latombes-challenge-to-eu-us-data-transfers-fails); [A&O Shearman](https://www.aoshearman.com/en/insights/eu-us-data-privacy-framework-navigating-the-legal-landscape-after-the-general-courts-verdict)
- Art. 28 GDPR: a processor needs a binding contract. Art. 44 ff: transfers need adequacy (Art. 45) or safeguards (Art. 46). Art. 5(1)(e): storage limitation. Art. 25: data protection by design and by default. — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- The DSK TOM guidance (2025) recommends measures to avoid re-identification and data-protection-compliant data sources from the design phase onward. — [Uni Bonn ZMDT](https://www.jura.uni-bonn.de/de/forschung-und-lehre/interdisziplinaere-zentren/zmdt/neuigkeiten/dsk-orientierungshilfe)
- EDPB Guidelines 01/2025: pseudonymisation lowers risk but the output is still personal data for whoever can attribute it. — [Hunton](https://www.hunton.com/insights/publications/edpb-advises-on-pseudonymisation-for-gdpr-compliance)

### Inferences
- Use a Claude subscription for third-party scraped text only with the training opt-out set, and even then Anthropic is not contractually a processor under consumer terms. The owner discloses data to another controller, which needs its own Art. 6(1)(f) justification and must be named as a recipient. Safer options: the commercial API with the DPA, or route via the local model for raw text. [Medium]
- OpenRouter is a router to many upstream providers. Data protection status depends on OpenRouter's terms (logging, "no-training" or zero-data-retention provider filters) and on where the upstream providers are located; some are outside the US/EU and not under DPF. [Medium; OpenRouter terms not retrieved here]
- The local model is preferable for any pass over *unredacted* text (e.g. the redaction NER itself). [High as design principle]
- Suggested retention (my proposal, not from a source):
  - Raw snapshots: short (e.g. ≤ 90 days or until redaction plus QA is verified), then delete or keep only hashes and URLs.
  - Redacted corpus and labels: for the life of the model plus a reproducibility window.
  - Logs of LLM calls: no content.
- **Harness checks:**
  - Every labeling call goes through an allowlisted provider/endpoint config with a "DPA in place / training opt-out verified / DPF-listed or EU" flag; block others.
  - OpenRouter requests carry the ZDR/no-training provider filter.
  - No unredacted text leaves the machine (pre-send PII scan, fail closed).
  - Retention TTL jobs, plus an assertion that no raw snapshot is older than N days.
  - Redaction recall measured on a gold sample every release.
- **Human decisions:**
  - Choice of provider tier (consumer subscription vs. API).
  - Accepting OpenRouter upstream providers.
  - Retention durations.
  - Periodic DPF certification check (could be partly automated against the dataprivacyframework.gov list).

### Gaps
- Whether Latombe was appealed to the CJEU, and its status as of Oct 2026, was not confirmed. Monitor this.
- OpenRouter's data policy and DPA were not retrieved.
- Whether Anthropic's Claude Code subscription terms changed after Sept 2025 was not checked.

## 7. DPIA (Art. 35), DSK Muss-Liste, records of processing (Art. 30(5))

### Takeaway
A DPIA is not clearly mandatory, but it is advisable. Large-scale scraping with likely Art. 9 content, new technology (AI) and invisible processing meet several WP248 criteria, and CNIL expects DPIAs for risky scraping. The Art. 30(5) exemption for fewer than 250 employees does *not* apply, because the processing is not occasional and includes special categories. Keep a lightweight Art. 30 record. [Medium]

### Cited Findings
- The DSK published an Art. 35(4) list of processing operations requiring a DPIA (Muss-Liste, non-public sector), including evaluation or scoring and automated decisions; German Land DPAs publish versions of it. — [HmbBfDI DSFA Muss-Liste nicht-öffentlicher Bereich (2018)](https://datenschutz-hamburg.de/fileadmin/user_upload/HmbBfDI/Datenschutz/Informationen/DSFA_Muss-Liste_fuer_den_nicht-oeffentlicher_Bereich_-_Stand_17.10.2018.pdf); [LfD SH Muss-Liste](https://datenschutzzentrum.de/uploads/datenschutzfolgenabschaetzung/20180525_LfD-SH_DSFA_Muss-Liste_V1.0.pdf)
- CNIL (2025): a DPIA may be required where scraping presents particular risks (massive volume, sensitive data, vulnerable persons, difficulty exercising rights). — [Blog du Modérateur](https://www.blogdumoderateur.com/ia-cnil-autorise-web-scraping); [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/06/web-scraping-for-ai-development--the-cnil-builds-on-edpb-guidanc.html)
- The EDPB connected-vehicle guidelines also recommend an early DPIA given the scale and sensitivity of vehicle data. — [Hogan Lovells](https://www.hoganlovells.com/en/publications/how-much-can-your-car-know-about-you-eu-guidelines-on-data-protection-and-connected-vehicles)
- Art. 30(5) GDPR: records duties do not apply to organisations with fewer than 250 employees *unless* the processing is likely to result in a risk, is not occasional, or includes Art. 9/10 data. — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)

### Inferences
- The relevant Muss-Liste items were not individually verified. Items about large-scale processing of data on behaviour, or of special categories, may be triggered depending on scale. [Low-Medium]
- A combined "LIA + DPIA-lite" document per data pipeline (scout corpus; sensor datasets) is proportionate for a one-person project. [Medium]
- There is no DPO obligation: § 38 BDSG uses the threshold of 20 persons constantly processing data, or a mandatory DPIA, or business-like processing for transfer. A mandatory DPIA would in theory trigger § 38(1) sentence 2. — [BDSG § 38](https://www.gesetze-im-internet.de/bdsg_2018/__38.html). [Medium; the edge case is worth a human check]
- **Harness checks:**
  - An Art. 30 record (YAML) exists and lists every pipeline, data category, recipient, transfer and retention.
  - It is consistent with the configs (providers, TTLs).
  - The DPIA/LIA document exists, and its version date is newer than the last change to source registry or provider list.
- **Human decision:** whether a formal DPIA is required (this also triggers the § 38 BDSG DPO question), and its sign-off.

### Gaps
- The current DSK Muss-Liste item numbering (version 1.1) was not fetched and verified.
- No DSK statement found on whether AI training on scraped data is per se on the list.

## 8. German DPA guidance: DSK OH KI (May 2024), DSK TOM guidance (2025), HmbBfDI and LfDI BW papers

### Takeaway
The DSK OH "KI und Datenschutz" (6 May 2024) targets *deployers* of AI applications. The DSK OH on TOMs for development and operation of AI systems (June 2025) targets developers and spans design, development, introduction and operation, but expressly excludes scraping legality. The HmbBfDI July 2024 discussion paper (LLMs do not store personal data) remains a regional discussion paper. EDPB Opinion 28/2024 adopted a different, case-by-case test that prevails in practice. [Medium-High]

### Cited Findings
- DSK Orientierungshilfe KI und Datenschutz, 6 May 2024. — [DSK PDF](https://www.datenschutzkonferenz-online.de/media/oh/20240506_DSK_Orientierungshilfe_KI_und_Datenschutz.pdf); [Dr. Datenschutz summary](https://www.dr-datenschutz.de/datenschutz-bei-ki-die-neue-dsk-orientierungshilfe/)
- DSK OH "Empfohlene technische und organisatorische Maßnahmen bei der Entwicklung und beim Betrieb von KI-Systemen", adopted June 2025 (dated 17 June 2025). It is aimed at developers and manufacturers, structured in four lifecycle phases, and covers data-protection-compliant data sources, avoiding re-identification, bias analysis, federated learning and intervenability (deletability of training data). Collection by crawling or scraping is not its subject. — [DSK OH KI-Systeme PDF](https://www.datenschutz-berlin.de/fileadmin/user_upload/pdf/publikationen/DSK/2025/20250617-DSK-OH_KI-Systeme.pdf); [Uni Bonn ZMDT](https://www.jura.uni-bonn.de/de/forschung-und-lehre/interdisziplinaere-zentren/zmdt/neuigkeiten/dsk-orientierungshilfe); [Stiftung Datenschutz](https://stiftungdatenschutz.org/veroeffentlichungen/datenschutzwoche/detailansicht/datenschutzwoche-vom-23-juni-2025-585)
- A DSK Entschließung (2025) calls for GDPR adjustments concerning AI. — [DSK Entschließung 2025](https://www.datenschutz-berlin.de/fileadmin/user_upload/pdf/publikationen/DSK/2025/2025-DSK-Entschliessung-DSGVO-KI-Anpassungen.pdf)
- HmbBfDI discussion paper, 15 July 2024: argued that storing an LLM does not amount to processing personal data. — [CMS update Aug 2024](https://service.betterregulation.com/sites/default/files/cms-data-protection-update-eu-and-germany-august-2024.pdf); [Digital Policy Alert](https://digitalpolicyalert.org/change/10382-discussion-paper-on-the-nexus-between-the-general-data-protection-regulation-and-large-language-models). Academic commentary says the EDPB "had no choice but to reject" the argument that storing an ML model *never* processes personal data. — [European Law Blog PDF](https://www.europeanlawblog.eu/pub/zh4uxsfq/download/pdf)
- EDPB support-pool report "AI Privacy Risks & Mitigations – LLMs" (10 April 2025, expert Isabel Barbera) gives a risk-management methodology and mitigations. It is a report, not EDPB guidance. — [EDPB page](https://www.edpb.europa.eu/our-work-tools/our-documents/support-pool-experts-projects/ai-privacy-risks-mitigations-large_pt); [Digital Policy Alert](https://digitalpolicyalert.org/event/29003-european-data-protection-board-released-report-on-artificial-intelligence-privacy-risks-and-mitigations-in-large-language-models)

### Inferences
- For a German controller, the competent authority is the Land DPA of the owner's residence. Whether HmbBfDI is relevant depends on where the owner lives. Even so, after Opinion 28/2024 (an Art. 64(2) opinion that all DPAs follow in consistency matters), the Hamburg thesis should be cited only as minority or historical context. [Medium]
- The 2025 DSK TOM paper is the best German checklist source for harness controls in the development phase. [Medium]

### Gaps
- The LfDI Baden-Württemberg discussion paper "Rechtsgrundlagen im Datenschutz beim Einsatz von KI" (versions 2023–2024) and any 2025–2026 update were not retrieved.
- Whether HmbBfDI formally withdrew or updated its paper after Dec 2024 was not confirmed.

## 9. Memorisation and regurgitation; verbatim quotes in model cards and eval reports

### Takeaway
Published weights may count as personal data if extraction is more than negligible (EDPB standard). The bigger practical risk for scout-large lies in *published artefacts*: verbatim quotes in model-card examples, eval reports, error analyses and any dataset compendium. Those are plain publication of personal data, for which the analysis in § 1 and § 2 applies in full. The current choice of fictional examples is the right control. [Medium-High]

### Cited Findings
- Anonymity requires negligible probability of extraction, including through queries, assessed with means reasonably likely to be used by anyone, which counts for publicly released models. — [CMS on EDPB Opinion 28/2024](https://cms.law/en/int/legal-updates/edpb-opinion-28-2024-key-takeaways-on-processing-personal-data-in-the-context-of-ai-models)
- SRB: personal opinions in comments "relate to" their author. A verbatim quote of a forum post is therefore personal data wherever its author is identifiable, e.g. via a web search for the quote. — [Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/09/pseudonymized-data-after-edps-v-srb.html)
- The EDPB LLM risk report (2025) catalogues regurgitation and extraction risks and mitigations. — [EDPB page](https://www.edpb.europa.eu/our-work-tools/our-documents/support-pool-experts-projects/ai-privacy-risks-mitigations-large_pt)

### Inferences
- A verbatim quote from a public post is re-identifiable by searching for it even after usernames are redacted. Redaction does not make published quotes anonymous. [High]
- scout-large outputs spans of the *user-supplied* input, so regurgitating training text through inference is unlikely. Weights-level membership inference is the residual risk. [Medium]
- **Harness checks:**
  - n-gram overlap scan (e.g. ≥ 8–10 consecutive tokens, threshold to be decided) between every published artefact (model card, README, eval reports, example JSON, Space demos) and the training/eval corpus. Fail on a hit.
  - PII/NER scan of published artefacts.
  - Assert that "fictional examples" are tagged as synthetic, with generation provenance.
  - Membership-inference or canary test per release, with the result recorded in the card.
  - Eval reports publish aggregate metrics only, no per-example text from scraped sources.
- **Human decisions:**
  - Threshold values.
  - Whether to quote public-sector texts verbatim (parliamentary records are public documents, but MPs' and witnesses' names are still personal data; likely acceptable with a separate rationale).

### Gaps
- No standard regulator-endorsed test or threshold for "negligible" extraction risk was found.

## 10. Human-subject datasets (UCI HAR); checks before re-hosting third-party datasets

### Takeaway
UCI HAR (30 volunteers, smartphone IMU) is pseudonymous rather than anonymous in the GDPR sense. Research shows accelerometer and gait signals can re-identify individuals, and subject IDs are kept. In the hands of a downstream user without auxiliary data, the SRB relative approach makes it arguably non-personal. Training on it is low risk. *Re-hosting* or curating it in a compendium makes the owner a distributor, so check the license, original consent or ethics statement, and existing de-identification first. Linking to the original source is safer than mirroring it. [Medium]

### Cited Findings
- Studies show motion-sensor data allows re-identification: one reports an average 96% re-identification risk from a full day of wrist-worn sensor data, with risk rising with activity intensity. Others identify people by accelerometer gait signals. — [NSF PAR paper](https://par.nsf.gov/servlets/purl/10358383); [HVL "Wearables in Arthritis"](https://hvlopen.brage.unit.no/hvlopen-xmlui/handle/11250/3107968); [Na et al., JAMA Netw Open via PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6324329)
- Gait data is privacy-sensitive and hard to anonymise because it is highly redundant and interdependent. — [arXiv 2203.04179](https://arxiv.org/pdf/2203.04179v1)
- SRB: data may be non-personal for a recipient lacking means reasonably likely to be used for re-identification. — [Bird & Bird](https://cm.twobirds.com/en/insights/2025/eu-the-srb-decision-a-new-era-for-personal-data-and-data-processing-agreements)
- Art. 9(1) GDPR: biometric data processed *for the purpose of uniquely identifying* a person is a special category. HAR training (activity recognition) does not have that purpose. — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- MIMII is machine-sound data. No personal data is expected beyond possible background speech; this was not verified.

### Inferences
- For UCI HAR at 50 Hz windows with only 30 subjects, there is no realistic auxiliary dataset for a downstream user to link it to. Re-identification of named persons is improbable, but the data is not formally "anonymous" under the strict EDPB view. [Medium-Low]
- **Harness checks for each third-party dataset in the compendium** (a dataset manifest with required fields):
  - License and redistribution rights.
  - Original publisher and DOI.
  - Whether human subjects are involved.
  - Consent or ethics statement URL.
  - Direct identifiers present (y/n).
  - Subject IDs present.
  - Location or timestamps present.
  - Free-text fields present.
  - Audio with speech present.
  - Decision on "link vs. mirror".
  - Takedown contact.
  - Fail if fields are missing or if human-subject data is set to mirror without an approved review.
- **Human decision:** go/no-go per human-subject dataset, and wording of the dataset card's "personal data" section.

### Gaps
- UCI HAR's original consent terms (Anguita et al. 2013) and license were not retrieved. Check the UCI page, which is CC BY 4.0 per general knowledge; this was not verified here.
- No German DPA guidance found on re-hosting third-party research datasets.

## 11. CAN bus logs (ROAD, can-train-and-test): personal data?

### Takeaway
Yes, vehicle data can be personal data. The EDPB treats journey details, driving style, distance and even technical data such as wear as indirectly identifying, because they relate to the driver or owner. VINs, GPS and timestamps make it direct. Public research CAN logs from test vehicles are probably low risk, but each one needs a check for VIN, GPS and time fields and for driver identity. [Medium-High]

### Cited Findings
- EDPB Guidelines 01/2020 on connected vehicles (v2.0, 9 March 2021): personal data includes directly identifiable data (driver identity) and indirectly identifiable data such as journey details, usage data (driving style, distance) and technical data (wear and tear). A DPIA early in design is recommended because of scale and sensitivity. — [Hogan Lovells](https://www.hoganlovells.com/en/publications/how-much-can-your-car-know-about-you-eu-guidelines-on-data-protection-and-connected-vehicles); [CMS](https://cms.law/en/aut/legal-updates/EDPB-issues-guidelines-on-Connected-Cars); [EDPB guidelines PDF](https://edpb.europa.eu/sites/default/files/consultation/edpb_guidelines_202001_connectedvehicles.pdf)
- The EDPB published a summary of the connected-vehicles guidance in May 2026. — [EDPB summary PDF](https://www.edpb.europa.eu/system/files/2026-05/edpb-summary-connected-vehicles_en.pdf) (content not reviewed)

### Inferences
- ROAD and can-train-and-test are recorded mostly on test vehicles driven by researchers, with arbitration IDs and payloads. Without a VIN, GPS or a driver link, they are close to non-personal for downstream users (SRB). Some CAN signals, such as decoded GPS or VIN broadcast frames, can still embed identifiers. [Medium-Low; dataset contents not verified]
- **Harness checks:**
  - Scan CAN logs for VIN patterns (17-character ISO 3779 regex in decoded ASCII payloads, plus UDS service 0x22 DID F190 responses).
  - Scan for GPS-like signal ranges if a DBC is available.
  - Check absolute timestamps.
  - Record the dataset manifest fields as in § 10.
- **Human decision:** acceptance per dataset when any identifier is detected.

### Gaps
- The actual field contents of the ROAD and can-train-and-test datasets were not inspected in this research.
- No source was found on whether these public datasets contain VIN frames.

## Summary: automated harness vs. human decisions (cross-cutting)

### Takeaway
Most controls are mechanical and can be enforced as CI gates. The owner keeps a small set of judgement calls that cannot be automated.

### Cited Findings
- Basis for automation: data protection by design and by default (Art. 25), accountability (Art. 5(2)), and the DSK 2025 lifecycle TOMs. — [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj); [DSK OH KI-Systeme](https://www.datenschutz-berlin.de/fileadmin/user_upload/pdf/publikationen/DSK/2025/20250617-DSK-OH_KI-Systeme.pdf)

### Inferences
- **Automatable gates (fail closed):**
  1. Source registry with legal-basis and LIA ID, and robots.txt/ai.txt state captured.
  2. Denylist and suppression list applied at fetch, label and train.
  3. Pre-send PII scan; no unredacted text goes to any non-local LLM.
  4. Provider allowlist with DPA, training opt-out, ZDR and DPF/EU flags.
  5. Sensitive-category quarantine.
  6. Retention TTL assertions.
  7. Provenance for every training example.
  8. Memorisation or MIA test per release.
  9. n-gram overlap and PII scan of all published artefacts.
  10. Privacy notice exists, is linked from every card, and matches registry and providers.
  11. Art. 30 record consistent with configs.
  12. Dataset manifest completeness for third-party datasets.
  13. VIN/GPS scan for vehicle data.
  14. Rights-register SLA tracking.
- **Human decisions (sign-off, ideally in an AskUserQuestion-style release gate):**
  - Accept controller status and contact details.
  - Approve the LIA per source class and the DPIA-required question (plus the § 38 BDSG consequence).
  - Choose LLM provider tiers.
  - Set retention periods.
  - Decide on keeping sensitive-but-relevant content (e.g. accessibility or health mobility pains).
  - Set thresholds (redaction recall, n-gram length, MIA).
  - Whether to call a model "anonymous" (recommendation: do not).
  - Approve mirroring of human-subject datasets.
  - Decide objection requests if not auto-granted.
  - Retrain or withdraw after a memorisation finding.

### Gaps
- Unsettled law to monitor:
  - The Digital Omnibus (Art. 88c/88bis, personal data definition); Council general approach pending as of Sept 2026.
  - A possible CJEU appeal of Latombe.
  - EDPB anonymisation guidance.
  - Any CJEU ruling on AI training and Art. 9.
