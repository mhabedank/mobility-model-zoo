# Research: one identity, taken from the website imagery

What was measured rather than assumed, and the three places where a measurement overturned a
decision that looked obvious.

## R1 — The palette of the imagery, sampled not guessed

The series file `zoo/site/images/series/siebdruck.yaml` records the palette as Lab anchors for
check I6, not as hex. The working values were sampled from the built renders instead:

| Role | Value |
| --- | --- |
| Ground and shadow | `#062544`, down to `#001530` |
| Paper and light | `#FBEED0` |
| Sky and structure | `#A5DBC6` |
| Mist and distance | `#6C928C` |
| The one warm accent | `#ED9B20`, deepening to `#CA6A0A` |

The old interface used `#1B3BD8` and `#6FFFC8`. Neither appears anywhere in any illustration,
which is the measurable form of the complaint that started the work.

## R2 — Cream is light, not surface

The first palette put cream `#F8F3E6` on the page. It reads yellowed, and the reason is visible
in the images: cream is a narrow band of horizon light there, never a field. The large field is
navy, and the light part of every illustration is cool pale mint.

Moving the page tone to a cool `#EDF3EF` removed the patina. The same tone then returns as the ink
of the night print, which makes the two schemes one pair rather than two inventions. Cream now
survives only where something is actually printed: the mark's ground and the motif strokes.

## R3 — The mid-tone, measured against the plate

Carrying the imagery's mist tone `#6C928C` into the motifs made their structure sink. Measured
against the plate `#062544`:

| Mid-tone | Contrast on the plate | Verdict |
| --- | --- | --- |
| `#6F7DC4`, the old grey-violet | 4.35:1 | weakest element of the old plate |
| `#6C928C`, mist from the images | 4.52:1 | passes, but structure sinks |
| `#A5DBC6`, pale mint | 9.99:1 | structure reads |

The mist tone is not a contrast failure; it clears the 3:1 the plate requires. It fails for a
different reason, which the numbers only half explain: in the illustrations that tone carries
distance and haze, never structure, and used for structure it reads as muddy. Pale mint is both
the tone the images use for structure and, by a wide margin, the legible one.

## R4 — Thirty-six pairs before a line was written

Every colour pair that carries meaning was computed before the tokens were applied: body text on
each surface, secondary text, links, button labels, the three chip pairs, the focus ring, strong
borders and the three series colours, in both schemes. All 36 passed on the first pass; the
thinnest were strong borders at 3.19:1 and series B at 3.31:1 against a threshold of 3. The
browser accessibility run confirmed it afterwards on the rendered page.

## R5 — `stroke-linecap="square"`, not path surgery

The motifs were to be cut from round caps to flat ones. The obvious route was to extend every
open run by half a stroke width to make up for the cap that was lost, which meant editing
geometry in fifteen files and left three zero-length runs in `hum-fan` that exist only as round
caps and would have vanished silently.

A square cap covers exactly what a round cap covered and ends flat. No geometry changes, arcs are
correct without special handling, the zero-length runs still draw, and the whole change is one
attribute per file. The first approach was written and then thrown away.

## R6 — The width axis is real, but not where it was first looked for

Archivo's width axis is the argument for choosing it. Fetched through the Google Fonts CSS API it
does not arrive, whatever is requested. Measured, at 46 px, "affordable and better":

| Source | wdth 100 | wdth 78 | wdth 125 |
| --- | --- | --- | --- |
| Google Fonts CSS API | 419.1 px | 419.1 px | 419.1 px |
| `Archivo[wdth,wght].ttf` from the repository | 453.2 px | 372.7 px | 579.3 px |

The first result was taken at face value for one round and produced a comparison panel that was
narrower only in the caption. Measuring the rendered width, rather than looking at it, is what
caught it.

## R7 — Shipping size, in two steps

| Step | Size |
| --- | --- |
| `Archivo[wdth,wght].ttf`, full | 643 KB |
| Subset to the 222 code points Figtree covered | 82 KB |
| Axes first trimmed to wght 400–800, wdth 78–100 | 51.3 KB |

Matching the outgoing font's character set rather than a guessed Latin range is what keeps
`og.LATIN_RANGES` and its test valid across the swap. Archivo's own default weight is 600, which
is unusual but upstream; CSS always requests a weight, so it does not surface.

## R8 — What stops a scroll is the picture

Four share-card treatments were mocked at 552 px in a LinkedIn feed: today's indigo-and-neon,
the poster palette quiet, the poster palette loud, and an illustration carrying the card.

The neon survives in exactly one small status pill; orange does that job equally well, and cream
on navy is more legible at that size than white on indigo. The illustrated card beat all three
typographic ones, and not because of colour. The axis that matters is picture against type, not
neon against orange.

## R9 — PNG and the direction of scaling

Illustrated cards exceeded the per-card budget, and the obvious fix was to draw the smaller
derivative.

| Drawn at 1200 px from | Largest card |
| --- | --- |
| the 1600 derivative, downscaled | 395 KB |
| the 960 derivative, upscaled | 405 KB |

Upscaling interpolates and creates intermediate tones; flat colour fields compress best when they
stay flat, which means downscaling from a larger source. The hypothesis was wrong and the
measurement was cheap.

## R10 — The size budget was already spent

S1's site-wide total stood at 299,810 bytes of 300,000 before this branch touched anything: 190
bytes of headroom. The feature did not consume the budget, it revealed that the budget was gone.

The total is also not what guards the promise. SC-007 of feature 008 says a page loads its main
content in under two seconds on a typical mobile connection, and that is measured per page by S2
(Largest Contentful Paint under Fast 3G throttling and 4× CPU slowdown), S4 (bytes transferred)
and the unchanged 150 KB per page, whose heaviest page sits at 60 KB. The site-wide total is a
guard against creeping growth, since no visitor loads the whole site. It moved to 320 KB while the
guards that measure the promise stayed where they were and kept passing.

The same reasoning, more strongly, applies to the per-card limit O1: `assets/og/` is already
outside the site total because link-preview crawlers fetch those bytes, not readers.

## R11 — A check that was missing

When the text outgrew its panel on the illustrated card, the title ran into the line beneath it
and every check still passed: O2 measures margins and the centre square, and the title fitter
only measures width. It was caught by eye, which is not a method.

O2 now compares the sibling blocks — `mark` sits inside `brand` by design, the rest must never
meet — and the test was verified against the boxes of the broken layout, where it names
`title and line overlap`.
