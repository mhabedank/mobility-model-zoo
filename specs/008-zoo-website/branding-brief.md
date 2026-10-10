# Branding brief: prompt for Claude Design

Paste the prompt below into Claude Design together with `docs/hf-org/avatar-512.png` (the existing mark). The result feeds FR-024 of [spec.md](spec.md).

---

Extend the visual identity of **Mobility Model Zoo** from a logo into a web identity, and design two pages with it: the zoo's start page and the landing page of its first model, **scout-large**.

**The project**
Mobility Model Zoo is an open, non-commercial collection of small, fast machine learning models for mobility: product development, automotive security, condition monitoring. Every model runs locally (from a laptop down to a microcontroller), is measured on a frozen benchmark, versioned and published on Hugging Face with an honest model card. Its tone is calm, precise and technical: measured, not claimed. Think of the documentation sites of Linear, Mapbox, Vercel or Hugging Face, not of a transit app and not of a startup with a marketing hero.

**What exists and must stay**
- The mark (attached): a white, rounded, slightly italic "M" with a mint dot, on a royal blue square. Approximate colors: royal blue `#1B3BD6`, mint `#6CFFC8`, white. Sample the exact values from the image. Keep the mark unchanged; you may add a horizontal lockup with the wordmark "Mobility Model Zoo" and a monochrome version.

**scout-large in one paragraph**
scout-large finds jobs-to-be-done, pains and gains in German and English mobility texts (interviews, forum posts, reviews, studies) and returns each one as a verbatim quote with character offsets, its kind (job, pain, gain), a score, and the actor type, evidence type and evidence scope. On the frozen benchmark it reaches a comparison composite of 0.72 against 0.67 for the best zero-shot small model (agreement with two frontier reference models, not accuracy). It reads a 9,240-character interview in 8.1 s on 4 CPU cores with 2.5 GB of memory, in 0.84 s on a MacBook M3 Pro GPU and in 0.12 s on a DGX Spark, where it processes 1,260 texts per minute; the generative models it was compared with manage 0.4 to 10 per minute. Output format `jtbd-span-v1`, licence Apache-2.0.

**Deliverables**
1. **Design tokens** as CSS custom properties: a color set for light and dark mode built around the blue and mint (backgrounds, surfaces, text, muted text, borders, links, focus ring, code, and three semantic colors for the item kinds job, pain and gain that work as text highlights on both backgrounds); a type scale; spacing, radius and shadow rules (flat and quiet). Every text/background pair must meet WCAG 2.1 AA; list the contrast ratios.
2. **Typography**: one sans-serif for text and headings and one monospace for code, both under the SIL Open Font License, so they can be self-hosted. No Google Fonts links or other third-party loading.
3. **Components**, each in light and dark: header with mark and navigation; hero; a model tile for the start page (name, topic, task, latest version, status "published" or "in progress"); metric cards that always show the reference next to the number (for example "0.72 composite · vs. frontier reference models"); a code block with a copy button; a field table for an output schema; an **output viewer** that shows an input text with the quotes highlighted by kind next to the JSON output, linked both ways; a versions table; a callout for limitations; a footer with imprint, privacy notice, copyright policy and licence links.
4. **A visual idea for scout-large**: a sub-mark or a recurring graphic motif that fits the zoo's mark (scouting, finding, marking evidence in text) and can also work for later models (each model gets its own motif in the same system). No mascot.
5. **Chart style** for the two existing figures (quality against texts per minute; time to process 10,000 texts on four machines): colors for scout-large versus the comparison models, axis and label style, readable at mobile width.
6. **Two page mockups** as self-contained HTML (inline CSS, no external requests), desktop and mobile width, light and dark:
   - Start page: purpose of the zoo, topics (productdev, security, condition-monitoring), model list with scout-large published and four models in progress (picket-forest, picket-mlp, hum-fan, pace-cnn), the publishing principles (measured not claimed; immutable versions; open method, closed data; compliance).
   - scout-large page, in this order: hero with value proposition and one call to action to the quickstart; quickstart (pip install line, five-line Python example, output); interface (input, output fields, dimensions, format versioning); worked example in the output viewer; quality and speed with the two charts; intended use and out of scope; limitations; licence, provenance and AI Act note; versions; citation.

**Hard constraints**
- Content must be fully readable without JavaScript; scripts only for conveniences (copy, toggle, highlight linking).
- No cookies, no analytics, no third-party resources.
- No advertising, funding links, pricing, "contact sales", or any company branding; this is a private, non-commercial project.
- Numbers are never decorated as marketing claims: every metric carries its reference and its hardware.
- No stock photos, no 3D, no gradients behind text, no AI-cliché imagery (brains, glowing networks, robots).

End with a short note on the decisions you made and where the identity might still be weak.
