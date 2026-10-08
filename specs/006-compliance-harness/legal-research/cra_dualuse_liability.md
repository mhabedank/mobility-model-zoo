# EU product, security and trade rules beyond AI Act, GDPR and copyright for a private, non-commercial open-source mobility ML model zoo (Germany)

Status: research notes as of 2026-10-08. Not legal advice. "Adopted" = law in force; "draft/proposal" = not yet binding. Confidence levels: high / medium / low. Where a claim is from background knowledge and was not verified against a fetched source in this session, it is placed under Inferences or Gaps and marked "(unverified)". Several primary sources (EUR-Lex HTML, a PDF) could not be fetched by the tool; this is noted where relevant.

## 1. Cyber Resilience Act (Regulation (EU) 2024/2847)

### Takeaway
Adopted law. FOSS supplied outside a commercial activity (not monetised) is not "made available on the market", so the CRA's manufacturer obligations, including the 11 Sep 2026 reporting duty, do not apply to this project as long as nothing is monetised. The Commission's FOSS/scope guidance was approved as a draft on 27 July 2026 (C(2026) 5252) and keeps monetisation as the test. Confidence: high for "out of scope while non-monetised"; medium for edge cases (donations, model weights).

### Cited Findings
- Recital 18 text: "the provision of products with digital elements qualifying as free and open-source software that are not monetised by their manufacturers should not be considered to be a commercial activity." FOSS is understood as software whose source code is openly shared, licensed with all rights to access, use, modify and redistribute, and "developed, maintained and distributed openly, including via online platforms" — [Prighter, CRA recital 18](https://prighter.com/resources/laws/cyber-resilience-act/recitals/recital-18); [Presencis, CRA open-source exemption](https://presencis.com/regulations/cra/exemptions/open-source)
- Recital 18 also says the circumstances under which the product was developed, or how development was financed, should not be taken into account when determining commercial vs non-commercial character — [Presencis](https://presencis.com/regulations/cra/exemptions/open-source)
- The CRA does not regulate open-source software as a category; it regulates products "made available on the market", i.e. supplied "in the course of a commercial activity". Open-source software supplied outside a commercial activity is out of scope. Monetisation is the test: selling licences, selling support/consulting, dual licensing, paid hosted versions — [CRA Evidence, March 2026 draft guidance](https://craevidence.com/blog/cra-commission-guidance-march-2026) (secondary)
- Commission guidance: public feedback on the March 2026 draft closed 31 March 2026. The Commission approved the guidance as a draft on 27 July 2026 (document C(2026) 5252, ca. 80 pages); it is described as not formally adopted until all language versions are complete — [cyberresilienceact.eu, Commission guidance](https://www.cyberresilienceact.eu/commission-guidance.html)
- Guidance factors for commercial activity: selling software or paid editions, monetising services through the software, collecting personal data beyond what security/interoperability need, making donations effectively mandatory for access or updates. Not commercial: voluntary donations, sponsorships, public funding — [Open Source For You, July 2026](https://www.opensourceforu.com/2026/07/eu-clarifies-cra-rules-for-non-commercial-open-source/) (secondary). Note: this source also says paid consulting while software stays free is not commercial, which **conflicts** with [CRA Evidence](https://craevidence.com/blog/cra-commission-guidance-march-2026) listing "selling support or consulting around the software" as commercial. The final text should be checked.
- A monetised edition and a free community edition are treated as different products; the free edition is not placed on the market just because a paid one exists — [CRA Evidence](https://craevidence.com/blog/cra-commission-guidance-march-2026)
- Individual contributors (patches, bug fixes) "generally bear no CRA responsibility"; obligations fall on whoever controls releases and governance — [Open Source For You](https://www.opensourceforu.com/2026/07/eu-clarifies-cra-rules-for-non-commercial-open-source/). The guidance does not create a separate category for individual developers; the trigger is commercial activity — [cyberresilienceact.eu](https://www.cyberresilienceact.eu/commission-guidance.html)
- Open-source software stewards get a "defined, proportionate set of duties" (Art. 24) focused on supporting security and viability — [cyberresilienceact.eu](https://www.cyberresilienceact.eu/commission-guidance.html)
- Timelines: reporting of actively exploited vulnerabilities and severe incidents from 11 September 2026 for manufacturers and stewards; full application 11 December 2027 — [CRA Evidence](https://craevidence.com/blog/cra-commission-guidance-march-2026); [Open Source For You](https://www.opensourceforu.com/2026/07/eu-clarifies-cra-rules-for-non-commercial-open-source/)
- 22 Commission examples on when open source falls under the CRA are collected at [cvdportal.com](https://cvdportal.com/cra-guidance/examples/when-open-source-falls-under-the-cra) (not fetched in detail)
- Neither summary of the guidance addresses whether AI models/weights or firmware source code are "products with digital elements" — [cyberresilienceact.eu](https://www.cyberresilienceact.eu/commission-guidance.html); [Open Source For You](https://www.opensourceforu.com/2026/07/eu-clarifies-cra-rules-for-non-commercial-open-source/)

### Inferences
- The project is not a "manufacturer" placing products on the market: no price, no paid support, no paid hosting, no mandatory donations, no personal-data collection. CRA obligations (Annex I essential requirements, conformity assessment, CE marking, SBOM, Art. 14 reporting from 11 Sep 2026) do not attach. Confidence: high.
- The project is not an "open-source software steward" either. Stewards are legal persons (other than manufacturers) that systematically and sustainably support FOSS intended for commercial activities (Art. 3(14), unverified wording). A private individual does not fit. Confidence: medium-high.
- Firmware and generated C code are software and could in principle be "products with digital elements" or components if monetised. Model weights are a grey zone: a stand-alone weights file arguably is data, not software, but once bundled with inference code or firmware it is part of a software product. This only matters if commercial activity starts. Confidence: medium.
- Risk triggers to keep out of the project (and to monitor automatically): GitHub Sponsors/Ko-fi tied to access or updates, paid support offers, paid hosted inference, telemetry collecting personal data, a company taking over releases. Voluntary donations look safe under the July 2026 draft guidance, but the final text should be checked.
- If a manufacturer integrates the code into a commercial product, the CRA's duties sit with that manufacturer (Art. 13(5) due diligence on components, unverified). Under Art. 13(6) (unverified) the manufacturer must report vulnerabilities it finds to the component maintainer, so the project may receive such reports. A SECURITY.md with a contact point covers this.
- Harness/documentation coverage: (a) a "CRA status" statement in README/org card: non-commercial FOSS, not placed on the market, no CE marking, not intended as a component without the integrator's own conformity assessment; (b) a CI check that no monetisation links/paid tiers exist in repo metadata (FUNDING.yml, model card), or a flag for owner review if they do; (c) SECURITY.md with a vulnerability contact (voluntary, but good practice and matches CRA expectations of integrators); (d) optional SBOM (CycloneDX/SPDX) generation for firmware builds as a goodwill measure for downstream integrators.

### Gaps
- Verbatim text of recital 19, Art. 3(14), Art. 24 and Art. 71 could not be fetched (EUR-Lex returned empty content). Dates are confirmed via secondary sources only.
- No confirmed statement in the 2026 guidance on AI model weights or firmware source as products with digital elements.
- Whether the final (all-language) guidance had been formally adopted by 2026-10-08 is unconfirmed.
- Conflicting secondary reports on whether paid consulting around free software is commercial activity.

## 2. EU dual-use export controls (Regulation (EU) 2021/821, Annex I as amended by Delegated Regulation (EU) 2025/2003) and US EAR

### Takeaway
Adopted law. Defensive CAN intrusion-detection models are not "intrusion software" and very likely fall under no Annex I entry. Attack research documents (fuzzing, masquerade, replay, GNSS spoofing, V2X misbehaviour) published openly without restrictions benefit from the "in the public domain" exemptions in the General Technology Note and General Software Note. This assumes they are actually published, not shared privately first. Under US EAR, published open-source software and technology is "not subject to the EAR" (§734.7). Encryption source code is the one area that historically needed a notification. Confidence: medium-high for the ML models; medium for attack research (depends on depth and operational detail).

### Cited Findings
- Commission Delegated Regulation (EU) 2025/2003 of 8 September 2025 amends Annex I of Regulation 2021/821; published in the OJ on 14 November 2025, in force 15 November 2025. It implements 2024 regime list changes and additional Wassenaar commitments — [EUR-Lex 2025/2003](https://eur-lex.europa.eu/eli/reg_del/2025/2003/oj/eng); [Baker McKenzie](https://sanctionsnews.bakermckenzie.com/eu-and-uk-update-their-respective-dual-use-export-control-lists-key-changes-and-implications-for-exporters/); consolidated text [CELEX 02021R0821-20251115](https://eur-lex.europa.eu/eli/reg/2021/821/2025-11-15/eng)
- Definition: "Intrusion software" means software specially designed or modified to avoid detection by 'monitoring tools' or to defeat 'protective countermeasures' of a computer or network-capable device, and performing extraction of data or modification of system/user data, or modification of the standard execution path to allow execution of externally provided instructions — [Nicola Bernard, summary of 2021/821](https://nicola-bernard.de/en/updated-eu-dual-use-regulation-is-now-in-force/); consolidated text above
- 4D004 controls software specially designed for the generation, operation or delivery of, or communication with, "intrusion software"; 4E001.c controls technology "required" for the "development" of "intrusion software" — [Federal Register 2015 (Wassenaar implementation background)](https://www.govinfo.gov/content/pkg/FR-2015-05-20/html/2015-11642.htm); [legislation.gov.uk Annex I Cat 5 Part 2](https://www.legislation.gov.uk/eur/2009/428/annex/I/division/7/division/part+2+information+security)
- Cryptography Note (5A002/5D002): releases mass-market items that are generally available to the public, need little support and have crypto functionality the user cannot easily change — [UK Notice to exporters 2018/07](https://www.gov.uk/government/publications/notice-to-exporters-201807-guidance-on-the-cryptography-note/notice-to-exporters-201807-guidance-on-the-cryptography-note)
- Exemptions: "In the public domain" = software or technology "available without restrictions upon its further dissemination" (copyright restrictions do not remove public-domain status). "Basic scientific research" = experimental or theoretical work undertaken mainly to gain new knowledge of fundamental principles, not primarily directed towards a specific practical aim — [University of Liverpool, export control exemptions](https://www.liverpool.ac.uk/legal/exportcontrols/exemptionsfortheacademiccommunity/)
- German practice: technical assistance does not require a licence where the information is "allgemein zugänglich" or "Grundlagenforschung" in the sense of the General Technology Note — [AWV §52b, gesetze-im-internet.de](https://www.gesetze-im-internet.de/awv_2013/__52b.html)
- US EAR §734.7: unclassified technology or software is "published", and not subject to the EAR, when made available to the public without restrictions on further dissemination — [eCFR 15 CFR 734.7](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.7)
- BIS: "publicly available" encryption source code is not subject to the EAR once the email notification under §742.15(b) is sent. Incorporating open source into a new item does not automatically exempt the new item — [BIS, encryption items not subject to the EAR](https://www.bis.gov/learn-support/encryption-controls/encryption-items-not-subject-to-ear); [EFF explainer](https://www.eff.org/deeplinks/2019/08/us-export-controls-and-published-encryption-source-code-explained)

### Inferences
- CAN-IDS anomaly detectors (defensive classifiers) do not avoid detection, do not extract data and do not alter execution paths, so they are not "intrusion software" and not 4D004 software. Nothing in Cat 4 or Cat 5 Part 2 appears to cover a binary/anomaly classifier. Confidence: high.
- Firmware using standard crypto libraries (e.g. mbedTLS on ESP32) for ordinary authentication/TLS is typically released by the Cryptography Note and, when published, by the public-domain exemption. Background (unverified): the EU General Software Note's public-domain release reportedly does not apply to Cat 5 Part 2 software, so a crypto-heavy item would rely on the Cryptography Note instead. Confidence: medium. The project should avoid custom/"non-standard" cryptography.
- Attack research: conceptual descriptions of attack classes (fuzzing, masquerade, replay, GNSS spoofing, V2X misbehaviour) and datasets/simulations meant to train detectors are not "technology required for the development of intrusion software". These attacks target automotive buses/radio signals, and the intrusion-software definition centres on defeating countermeasures of computers/network-capable devices. Even if some material came close, publishing openly without restrictions makes it "in the public domain". Risk factors to avoid: weaponised, ready-to-use attack tools against specific vehicle ECUs that evade detection, and non-public pre-release sharing with recipients outside the EU (that sharing is the export). GNSS spoofing *hardware/jammers* may touch other controls and radio law; publish analysis and synthetic data, not jammer designs. Confidence: medium.
- Hosting on US platforms (HF, GitHub): published, unrestricted software and technology is outside the EAR (§734.7). Gated access on HF (click-through) is arguably still "without restrictions on further dissemination" if anyone can accept. Approval-based gating could undermine "published" status. Confidence: medium.
- Harness/documentation coverage: (a) export-control self-classification note per release: "EAR99 / not subject to EAR as published; EU: not listed / public domain per GTN/GSN"; (b) a check that no repo contains non-standard cryptography or "intrusion software"-like tooling (keywords and owner review gate for attack code); (c) rule: attack research is published openly at once (no private pre-release to non-EU recipients); (d) keep attack content at the level of description, simulation and labelled data rather than operational exploit tooling.

### Gaps
- The exact 2025/2003 changes in Cat 4/5 (e.g. any new cyber entries) could not be read in full. EUR-Lex text not fetchable.
- No BAFA-specific guidance found on ML models or intrusion-detection publications.
- Whether BIS removed the §742.15(b) notification for standard-crypto open source in a 2021 rule (background knowledge suggests a 2021 rule limited notification to "non-standard cryptography") was not confirmed in fetched sources.

## 3. Product Liability Directive (EU) 2024/2853 and German transposition

### Takeaway
Adopted directive. Software (including AI systems) becomes a "product", but free and open-source software developed or supplied outside a commercial activity is excluded. Germany's government bill (BT-Drs. 21/4297) mirrors this and is scheduled to apply from 9 December 2026. The project is outside strict product liability while it stays non-commercial. Confidence: high for exemption; medium for German legislative status (final votes pending as of Aug 2026).

### Cited Findings
- Government bill "Gesetz zur Modernisierung des Produkthaftungsrechts", BT-Drucksache 21/4297 of 25 Feb 2026 — [Bundestag Drucksache 21/4297](https://dserver.bundestag.de/btd/21/042/2104297.pdf)
- Cabinet approval 17 Dec 2025; Bundesrat opinion 30 Jan 2026; first reading 4 Mar 2026; implements Directive 2024/2853; planned entry into force 9 Dec 2026 — [Bundestag hib](https://www.bundestag.de/presse/hib/kurzmeldungen-1150966)
- The bill excludes "Open-Source-Software, die außerhalb einer Geschäftstätigkeit entwickelt oder bereitgestellt wird" — [Bundestag hib](https://www.bundestag.de/presse/hib/kurzmeldungen-1150966)
- Where a component is FOSS developed or supplied outside a business activity, its maker is not liable under the new rules; software liability covers cloud and AI systems — [IHK Hannover](https://www.ihk.de/hannover/hauptnavigation/recht/wirtschafts-und-wettbewerbsrecht2/wettbewerbsrecht/neues-produkthaftungsgesetz-ab-dezember-was-aendert-sich--6966802); [Ebner Stolz](https://www.ebnerstolz.de/de/unser-angebot/leistungen/rechtsberatung/produktsicherheit-und-produkthaftung/neues-produkthaftungsgesetz-110227.html)
- Status: Legal Committee hearing mid-April 2026; as of August 2026 second/third reading and Bundesrat pending — [industrie-fachwissen.de](https://industrie-fachwissen.de/data/neues-produkthaftungsgesetz-2026-hersteller-importeure-software-haftung) (secondary)

### Inferences
- Not liable as a "manufacturer" under the new ProdHaftG while non-commercial. If the code or a model becomes a component of a commercial product, the integrating manufacturer is liable (and the PLD's recital 14 expressly does not want to burden non-commercial FOSS, unverified wording). Confidence: high.
- Same commercial-activity trigger as CRA, so a single "no monetisation" guard in the harness serves both regimes.
- Residual tort liability under §823 BGB (negligence) stays possible in theory. See section 8 for contractual limits.
- Harness/documentation: state non-commercial status in README/model cards. Keep a dated record (e.g. a release manifest with no pricing, sponsorship or paid-service fields) that can show non-commercial status at each release.

### Gaps
- Whether the Bundestag/Bundesrat passed the law between Aug and Oct 2026 could not be confirmed.
- Exact text of PLD recital 14 / Art. 2(2) not fetched (EUR-Lex unavailable).

## 4. Radio Equipment Directive delegated act (EU) 2022/30 / EN 18031

### Takeaway
Adopted law, applying since 1 August 2025, but only to radio equipment *placed on the market*. Publishing firmware source or generated C code for ESP32 is not placing radio equipment on the market. Not applicable. Confidence: high.

### Cited Findings
- Delegated Regulation (EU) 2022/30 activates RED Art. 3(3)(d), (e), (f) for internet-connected radio equipment and certain other categories; EN 18031-1/-2/-3:2024 are the harmonised standards; mandatory from 1 August 2025 for in-scope devices sold in the EU — [UL Solutions](https://www.ul.com/insights/new-cybersecurity-requirements-radio-equipment-directive); [UK government factsheet](https://www.gov.uk/government/publications/radio-equipment-regulations-2017/regulation-eu-202230-factsheet); [productip](https://productip.com/kb/productipedia/compliance-resources/cybersecurity-for-radio-equipment)

### Inferences
- RED obligations sit with manufacturers/importers/distributors of physical radio equipment. Software published on its own is not radio equipment. The hardware-in-the-loop bench built from purchased, CE-marked ESP32 dev boards for private use is not placed on the market either. Confidence: high.
- From 11 Dec 2027 the CRA largely takes over RED cybersecurity for products in its scope (background, unverified). Irrelevant while non-commercial.
- Documentation: one line in firmware READMEs: "Source code only. Anyone who builds and places devices on the EU market is responsible for RED (incl. EN 18031) and CRA conformity." Do not ship prebuilt devices or kits.

### Gaps
- None material. ESP32-specific guidance was not found (not needed).

## 5. UNECE R155/R156 and ISO/SAE 21434

### Takeaway
These bind vehicle manufacturers (type approval) and, through contracts, their suppliers. They do not bind a private publisher of research models. Prudent disclaimers should say the models are research artefacts, not developed under ISO/SAE 21434 or ISO 26262 processes, and not validated for production vehicles. Confidence: high (based on background knowledge; no source fetched in this session).

### Cited Findings
- No primary source fetched in this session (time budget). See Gaps.

### Inferences
- (unverified) UN R155 requires a certified Cyber Security Management System for vehicle type approval; UN R156 requires a Software Update Management System. Both are mandatory for new vehicles in the EU via the General Safety Regulation (EU) 2019/2144 since July 2024. ISO/SAE 21434 is a voluntary engineering standard often used as evidence. Obligations rest on the OEM, which flows requirements down to suppliers by contract.
- Recommended model-card disclaimer elements: "Research use only; not a safety- or security-certified component; not developed under ISO/SAE 21434, ISO 26262 or ISO/PAS 8800; no claims of fitness for type approval (UN R155/R156); integrators bear full responsibility for TARA, validation and approval." Also report the evaluation datasets (e.g. public CAN-IDS benchmarks) and known limitations (distribution shift across vehicles/OEMs, false-positive rates).
- Harness: lint model cards for the presence of the "out of scope: production vehicles / safety-critical deployment" section and the standards disclaimer.

### Gaps
- Primary UNECE texts and GSR 2019/2144 dates were not verified in this session.

## 6. Dual-use/misuse statements, platform policies and responsible disclosure

### Takeaway
GitHub explicitly allows dual-use security research and asks for a README disclaimer and a SECURITY.md contact. Hugging Face prohibits content meant to generate malware or gain unauthorised access, and offers gated access for sensitive artefacts. Defensive IDS models are low-risk. Attack-research documents should stay descriptive. Confidence: high.

### Cited Findings
- GitHub allows "posting of content that is used for research into vulnerabilities, malware, or exploits, as the publication and distribution of such content has educational value", but forbids "direct support of unlawful attacks that cause technical harms", e.g. delivering malicious executables or acting as attack infrastructure — [GitHub AUP: Active malware or exploits](https://docs.github.com/en/site-policy/acceptable-use-policies/github-active-malware-or-exploits)
- GitHub recommends: "Clearly identify and describe any potentially harmful content in a disclaimer in the project's README.md file or source code comments" and "Provide a preferred contact method for any 3rd party abuse inquiries through a SECURITY.md file". In cases of widespread misuse GitHub may put content behind authentication, or as a last resort disable it; appeals exist — [GitHub AUP](https://docs.github.com/en/site-policy/acceptable-use-policies/github-active-malware-or-exploits)
- Hugging Face prohibits "Content that attempts to transmit or generate malicious code (e.g., malware, trojans, viruses)" and "Content designed to disrupt, damage, or gain unauthorized access to systems or devices"; HF reserves moderation for evolving ML challenges; gated repos can require click-through conditions or maintainer approval — [Hugging Face Content Policy](https://huggingface.co/content-policy)

### Inferences
- For each security model card: an "Intended use" section (defensive detection, research, education), an "Out-of-scope use" section (no use to develop or tune attacks or evasion against real vehicles, no production deployment without own validation), a "Dual-use considerations" section, and a link to SECURITY.md.
- Attack-type research documents: describe mechanisms, threat models and detection signatures. Do not publish turnkey injection tools against named vehicle models, or detector-evasion recipes tuned to specific OEMs. If a real vulnerability in a specific vehicle/ECU is found, use coordinated disclosure with the OEM/supplier (and optionally BSI / Auto-ISAC) before publication, with a fixed embargo (e.g. 90 days).
- Gating: click-through gating on HF (accept terms) is compatible with the "public domain"/"published" export status. Approval-based gating could weaken that status (see section 2). Prefer open release for defensive models.
- Harness: (a) model-card linter requiring the sections above for repos tagged security/automotive-security; (b) SECURITY.md present in every GitHub repo and referenced from the HF org card; (c) keyword/owner gate before releasing anything under an "attack" directory.

### Gaps
- No HF policy text specific to security research/dual-use carve-outs was found; HF's policy does not explicitly exempt research.

## 7. German Impressum duty (§5 DDG, §18 MStV)

### Takeaway
Adopted law. §5 DDG (successor to §5 TMG since May 2024) applies to "geschäftsmäßige, in der Regel gegen Entgelt angebotene digitale Dienste". A purely private, non-commercial project with no advertising, affiliate links or monetisation generally does not need a DDG Impressum. §18(1) MStV exempts telemedia serving "ausschließlich persönlichen oder familiären Zwecken" (wording unverified). A public project presenting itself to a professional audience does not serve purely personal purposes, so a minimal name-and-address notice may still be prudent. §18(2) MStV (journalistic-editorial content) is unlikely to apply. Confidence: medium (unsettled for HF/GitHub org pages).

### Cited Findings
- The duty to provide provider identification is governed by §5 DDG and §18 MStV; §5 DDG targets "geschäftsmäßige digitale Dienste" — [IHK München, Impressum im Internet](https://www.ihk-muenchen.de/de/Service/Recht-und-Steuern/Internetrecht/Impressum-im-Internet/); [e-recht24](https://e-recht24.de/artikel/datenschutz/209.html)
- Purely private hobby blogs without advertising, affiliate links or business intent do not need an Impressum; this changes once monetisation occurs — [selbststaendigkeit.de](https://selbststaendigkeit.de/buchhaltung-fuer-gruender/impressum-kleinunternehmer/) (secondary)
- Those offering journalistic-editorial content must also observe §18(2) MStV — [datenschutz-generator.de](https://datenschutz-generator.de/ratgeber-impressum/)
- Comprehensive guidance also covering profiles on third-party platforms (social media etc.) — [datenschutz-generator.de](https://datenschutz-generator.de/ratgeber-impressum/); [LFK](https://lfk.de/impressumspflicht)

### Inferences
- HF org card and GitHub org page are profiles on third-party platforms. Courts have required an Impressum on social-media profiles where the use is business-like (background, unverified). For a non-commercial project: §5 DDG very likely not triggered. Under §18(1) MStV the "exclusively personal or family purposes" exemption is doubtful for a public, outward-facing model zoo. If an Impressum is given, the MStV minimum is name and address (ladungsfähige Anschrift). Confidence: medium-low.
- Option for the owner (decision, not a harness task): (a) no Impressum, relying on the private/non-commercial exemption, low but non-zero risk of warning letters (Abmahnung). Competitors' cease-and-desist claims require a competitive relationship, which is unlikely here. (b) A minimal Impressum (name + service address, e.g. a c/o address service) on a separate project website, linked from the HF org card. Avoid putting a home address on HF/GitHub.
- Monetisation (sponsoring buttons with rewards, ads, paid services) would trigger §5 DDG. The same "no monetisation" guard as for CRA/PLD covers it.
- Harness: check that the HF org card README and GitHub org profile either link to an Impressum/contact page or carry the documented decision. If a project website is added, check for Impressum and privacy notice links.

### Gaps
- Exact wording of §18(1) MStV and §5 DDG not fetched from gesetze-im-internet.de/landesrecht in this session.
- No case law found specific to HF or GitHub org pages.

## 8. Warranty/liability disclaimers: Apache-2.0 §§7–8 under German law

### Takeaway
Apache-2.0's blanket "AS IS" disclaimer (§7) and liability limitation (§8) are not fully enforceable in Germany. Free provision of OSS is generally treated as a gift (Schenkung). Under §521 BGB the donor is liable only for intent and gross negligence, under §524 BGB for defects only if fraudulently concealed (wording of §524 unverified). Liability for intent cannot be excluded (§276(3) BGB, unverified). If the licence counts as standard terms (AGB), clauses excluding liability for injury to life/body/health or gross negligence are void (§309 Nr. 7 BGB, unverified). No German court has ruled on OSS liability clauses. Confidence: medium.

### Cited Findings
- Free and permanent provision of open-source software is treated as a gift contract; under §521 BGB the donor is liable only for intent and gross negligence — [Uni Bremen course material](https://oncourse.uni-bremen.de/pluginfile.php/4642/mod_label/intro/k07_e02.pdf); [exali](https://www.exali.de/Info-Base/open-source-sicherheitsrisiken)
- Broad liability exclusions in OSS licences often do not survive AGB scrutiny. Contractual exclusion of liability for intent is not allowed in Germany; exclusions in GPLv2/v3 may be invalid; academic literature generally accepts the gift-contract view; German courts have not yet ruled on OSS warranty/liability exclusions — [exali](https://exali.de/Info-Base/open-source); [Ferner Alsdorf](https://www.ferner-alsdorf.de/gnu-general-public-license-gpl-ist-mit-deutschem-recht-vereinbar/); [Computerwoche](https://www.computerwoche.de/article/2887553/open-source-kostenlos-heisst-nicht-frei.html)
- Prototype Fund's legal knowledge base has a chapter "Verantwortung für Software und Inhalte" — [Prototype Fund KB](https://kb.prototypefund.de/books/rechtliche-grundlagen/page/verantwortung-fur-software-und-inhalte/export/pdf) (PDF not parseable by tool; not used as evidence)

### Inferences
- Practical liability exposure for a private, non-commercial publisher is low. It is limited to intent/gross negligence (gift privilege) plus fraudulently concealed defects, and strict product liability is excluded (section 3). Grossly negligent behaviour would be, e.g., publishing a model as "production-ready for vehicles" despite known severe flaws. Honest model cards with limitations and known failure modes are therefore the main liability control. Confidence: medium.
- Keep Apache-2.0 §§7–8 unchanged; they work "to the extent permitted by applicable law" (Apache's own wording, unverified here). Optional: add a short German-law note to README: "Liability according to statutory provisions for intent and gross negligence remains unaffected; otherwise the software is provided free of charge as a gift (§§ 521, 524 BGB)." Do not invent stronger exclusions; they would be void anyway.
- Model weights released under a separate licence (e.g. Apache-2.0 for weights, or a model licence) should carry the same disclaimer. Datasets' licences are covered elsewhere.
- Harness: check that LICENSE (Apache-2.0) and NOTICE are present, that model cards contain "Limitations / known failure modes" and "not for safety-critical use", and that no marketing language ("production-ready", "certified", "guaranteed") appears in cards or the org card (simple lint).

### Gaps
- §§521, 524, 276, 309 BGB wording not fetched from gesetze-im-internet.de in this session.
- No court decision on the effectiveness of Apache-2.0 §§7–8 in Germany found.

## Cross-cutting summary for the harness (synthesis of above)

### Takeaway
One fact drives most regimes: **no commercial activity / no monetisation** (CRA, PLD/ProdHaftG, §5 DDG). The rest is documentation: dual-use statements, automotive disclaimers, SECURITY.md, export self-classification, honest limitations.

### Cited Findings
- See sections 1, 3 and 7 for the shared commercial-activity trigger — [CRA Evidence](https://craevidence.com/blog/cra-commission-guidance-march-2026); [Bundestag hib](https://www.bundestag.de/presse/hib/kurzmeldungen-1150966); [IHK München](https://www.ihk-muenchen.de/de/Service/Recht-und-Steuern/Internetrecht/Impressum-im-Internet/)

### Inferences
- Automated checks: (1) monetisation guard (FUNDING.yml, sponsor links, pricing text, paid-API endpoints → block or owner gate); (2) model-card linter for intended use, out-of-scope use, dual-use, limitations, automotive standards disclaimer, export note; (3) SECURITY.md present in each repo and linked from the org card; (4) LICENSE/NOTICE present; (5) marketing-claim lint; (6) firmware README "source only, RED/CRA is the integrator's responsibility"; (7) attack-content gate requiring owner sign-off at release (aligned with the owner-approves-release workflow); (8) optional SBOM for firmware.
- Re-evaluation triggers to document: any monetisation, a legal entity taking over the project, prebuilt devices or kits being offered, private pre-release sharing of attack research with non-EU parties, and the final CRA guidance and ProdHaftG being formally adopted.

### Gaps
- Primary-text verification (EUR-Lex, gesetze-im-internet.de) was not possible with the fetch tool in this session. A follow-up pass should verify the statute wording marked "unverified".
