---
name: artelys-pptx
description: >
  Generate professional PowerPoint presentations using the Artelys brand template.
  Use this skill whenever the user asks to create slides, a deck, a presentation, or wants
  content turned into a PowerPoint — even if they do not explicitly mention Artelys or template.
  This skill handles everything: Artelys colors, white and navy logo variants in the footer,
  slide types (title, section divider, KPI cards, content+chart, timeline, tech stack,
  responsibility pillars, closing), and produces a downloadable .pptx file.
  Trigger on any request like "make slides about X", "create a deck for Y",
  "turn this into a presentation", or "generate a pptx".
---

# Artelys PPTX Skill

Generates polished `.pptx` files using the Artelys brand — colors, logos, footer — via **pptxgenjs**.

## Quick Start

1. Read the content/topic from the user's request or uploaded file
2. Write a Node.js script based on the patterns below
3. Run it: `cd /home/claude && node <script>.js`
4. Convert to PDF for QA: see [QA section](#qa)
5. Deliver via `present_files`

---

## Brand Constants

```js
const C = {
  navy:   "#16469C",   // Primary blue — dominant color
  orange: "#F25924",   // Main accent
  lblue:  "#00AFF0",   // Light blue accent
  pink:   "#B72075",   // Magenta accent
  warmOr: "#F8933A",   // Warm orange
  grey:   "#5B5B5B",   // Body text / muted
  lgrey:  "#F2F4F8",   // Card backgrounds
  white:  "#FFFFFF",
  black:  "#1A1A1A",
  footer: "#0D2C6B",   // Footer bar (darker navy)
};
```

## Logos

Both logos are pre-encoded in the skill's `assets/` folder. Load them at the top of every script:

```js
const path = require("path");
const SKILL_ASSETS = "/mnt/skills/user/artelys-pptx/assets";
// Navy logo — use on white/light backgrounds
const LOGO_NAVY  = "data:image/png;base64," + require("fs").readFileSync(path.join(SKILL_ASSETS, "logo_b64.txt"), "utf8").trim();
// White logo — use on dark/navy backgrounds (footer, dark panels)
const LOGO_WHITE = "data:image/png;base64," + require("fs").readFileSync(path.join(SKILL_ASSETS, "logo_white_b64.txt"), "utf8").trim();
```

---

## Slide Dimensions

**Always use `LAYOUT_WIDE` = 13.33 × 7.5 inches.** Never use 10 × 5.63.

```js
const W = 13.33, H = 7.5;
const FH = 0.42, FY = H - FH;      // footer height and Y position
const FL_W = 1.85, FL_H = 0.23;     // logo size in footer
const MX = 0.55;                     // horizontal margin
const CONTENT_Y = 1.18;             // Y position where content starts (below title+sublabel)
```

---

## Mandatory Footer

Every slide **must** have a footer. Call `footer(slide, presentationTitle)` at the end of each slide function.

```js
const DATE = new Date().toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" });

function footer(slide, title) {
  slide.addShape("rect", { x:0, y:FY, w:W, h:FH, fill:{color:C.footer}, line:{color:C.footer} });
  slide.addImage({ data:LOGO_WHITE, x:0.22, y:FY+(FH-FL_H)/2, w:FL_W, h:FL_H });
  slide.addText(title, { x:FL_W+0.4, y:FY, w:W-FL_W-1.8, h:FH,
    fontSize:8, color:"AABBD4", align:"center", valign:"middle", fontFace:"Calibri" });
  slide.addText(DATE, { x:W-1.4, y:FY, w:1.2, h:FH,
    fontSize:8, color:"AABBD4", align:"right", valign:"middle", fontFace:"Calibri" });
}
```

---

## Slide Types

### Title Slide

Split layout: left navy panel (logo + title) | right white panel (metadata blocks).

```js
function makeTitleSlide(pres, title, subtitle, author, meta) {
  const slide = pres.addSlide();
  const PW = 5.2;
  // Left navy panel
  slide.addShape("rect", { x:0, y:0, w:PW, h:H, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addShape("rect", { x:PW, y:0, w:0.08, h:H, fill:{color:C.orange}, line:{color:C.orange} });
  // Decorative circles (bottom of panel)
  slide.addShape("ellipse", { x:1.655, y:4.36, w:2.6, h:2.6, fill:{color:"1E3A7A", transparency:40}, line:{color:"1E3A7A"} });
  slide.addShape("ellipse", { x:0.945, y:4.848, w:1.7, h:1.7, fill:{color:"0F2560", transparency:30}, line:{color:"0F2560"} });
  // White logo top-left of panel
  slide.addImage({ data:LOGO_WHITE, x:0.42, y:0.48, w:3.7, h:0.46 });
  // Title text on panel
  slide.addText(title, { x:0.42, y:2.0, w:PW-0.6, h:1.5, fontSize:46, bold:true, color:C.white, fontFace:"Calibri" });
  slide.addText(subtitle, { x:0.42, y:3.75, w:PW-0.6, h:0.38, fontSize:15, color:"CCDDEE", fontFace:"Calibri", italic:true });
  // Right panel info blocks (label + value pairs)
  const RX = PW+0.55, RW = W-RX-0.45;
  meta.forEach((b, i) => {  // meta = [{label, value, color}]
    const by = 1.9 + i*1.35;
    slide.addShape("rect", { x:RX, y:by, w:0.06, h:0.85, fill:{color:b.color}, line:{color:b.color} });
    slide.addText(b.label, { x:RX+0.2, y:by, w:RW, h:0.3, fontSize:8, bold:true, color:b.color, fontFace:"Calibri", charSpacing:2 });
    slide.addText(b.value, { x:RX+0.2, y:by+0.32, w:RW, h:0.5, fontSize:16, color:C.black, fontFace:"Calibri" });
  });
  footer(slide, title);
}
```

### Content Slide Header (reusable helper)

Call at the start of every non-title slide:

```js
function slideHeader(slide, title, sub, accentColor) {
  slide.addShape("rect", { x:0, y:0, w:W, h:0.09, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addText(title, { x:MX, y:0.18, w:W-1.0, h:0.55, fontSize:26, bold:true, color:C.navy, fontFace:"Calibri" });
  if (sub) {
    slide.addText(sub.toUpperCase(), { x:MX, y:0.75, w:7, h:0.20, fontSize:8, bold:true, color:accentColor||C.orange, fontFace:"Calibri", charSpacing:2 });
    slide.addShape("rect", { x:MX, y:0.96, w:0.32, h:0.04, fill:{color:accentColor||C.orange}, line:{color:accentColor||C.orange} });
  }
}
```

### Section Divider

Full navy slide with large section number and circle decorations.

```js
function makeSectionSlide(pres, presTitle, num, sectionTitle, desc) {
  const slide = pres.addSlide();
  slide.addShape("rect", { x:0, y:0, w:W, h:H, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addShape("ellipse", { x:7.205, y:0.925, w:6.0, h:6.0, fill:{color:"1E3A7A", transparency:55}, line:{color:"1E3A7A"} });
  slide.addShape("ellipse", { x:6.128, y:0.3, w:3.8, h:3.8, fill:{color:"122B6A", transparency:35}, line:{color:"122B6A"} });
  slide.addText(`0${num}`, { x:MX, y:1.5, w:1.6, h:1.4, fontSize:80, bold:true, color:C.orange, fontFace:"Calibri" });
  slide.addShape("rect", { x:MX, y:3.1, w:0.07, h:1.5, fill:{color:C.orange}, line:{color:C.orange} });
  slide.addText(sectionTitle, { x:MX+0.25, y:3.05, w:8.0, h:0.95, fontSize:34, bold:true, color:C.white, fontFace:"Calibri" });
  slide.addText(desc, { x:MX+0.25, y:4.1, w:7.5, h:0.55, fontSize:15, color:"AABBDD", fontFace:"Calibri" });
  footer(slide, presTitle);
}
```

### Card Helper

Reusable card with optional accent color strip at top:

```js
function card(slide, x, y, w, h, accentColor) {
  // Subtle drop shadow
  slide.addShape("rect", { x:x+0.03, y:y+0.03, w, h, fill:{color:"D0DAE8"}, line:{color:"D0DAE8"} });
  // Card body
  slide.addShape("rect", { x, y, w, h, fill:{color:C.lgrey}, line:{color:"D8E2EE", w:0.5} });
  if (accentColor) slide.addShape("rect", { x, y, w, h:0.06, fill:{color:accentColor}, line:{color:accentColor} });
}
```

### Bullet Helper

```js
function bullet(slide, x, y, w, text, color, fontSize) {
  slide.addShape("ellipse", { x, y:y+0.05, w:0.28, h:0.28, fill:{color:color}, line:{color:color} });
  slide.addText(text, { x:x+0.38, y, w:w-0.38, h:0.5, fontSize:fontSize||13, color:C.black, fontFace:"Calibri", valign:"top" });
}
```

---

## Content-Driven Layout Helpers

> **Core principle: never hardcode card heights to fill the slide. Always derive height from content, then center the group in the available space.**
>
> `CH = FY - CONTENT_Y - 0.12` is forbidden for content cards — it produces blank white space when content is short and overflow when content is long.

### `cardH()` — compute card height from its content

Returns the height a card needs to hold its content comfortably.

```js
/**
 * Compute natural card height from its content.
 * @param {number} headerH   - Height reserved for the card title row (default 0.6)
 * @param {Array}  rows      - Each entry: { h } or just a number for the row height
 * @param {number} padTop    - Internal top padding (default 0.15)
 * @param {number} padBottom - Internal bottom padding (default 0.25)
 */
function cardH(rows, { headerH = 0.6, padTop = 0.15, padBottom = 0.25 } = {}) {
  const rowsTotal = rows.reduce((sum, r) => sum + (typeof r === 'number' ? r : r.h), 0);
  return padTop + headerH + rowsTotal + padBottom;
}

// Example — a card with a header and 5 bullet rows of 0.56in each:
const CH = cardH([0.56, 0.56, 0.56, 0.56, 0.56], { headerH: 0.5 });
```

### `centerGroupY()` — vertically center a content block

Returns the Y position that centers a block of known height between `CONTENT_Y` and `FY`.

```js
/**
 * Returns Y that centers a group of height `groupH` in the content area.
 * @param {number} groupH  - Total height of the content block (cards + gaps)
 * @param {number} topBias - 0 = perfectly centered, positive = shift up (default 0.1)
 */
function centerGroupY(groupH, topBias = 0.1) {
  const available = FY - CONTENT_Y;
  return CONTENT_Y + Math.max(0, (available - groupH) / 2) - topBias;
}

// Example — center a group of 3 KPI cards (each 1.78in tall, 0.18 gap):
const groupH = 3 * 1.78 + 2 * 0.18;
const CY = centerGroupY(groupH);
```

### `hCardRow()` — lay out N cards horizontally with auto-sizing

Returns an array of `{ x, y, w, h }` for each card, centered vertically as a group.

```js
/**
 * Compute geometry for a horizontal row of N equal-width cards.
 * @param {number} n      - Number of cards
 * @param {number} cardH  - Height of each card (from cardH() helper)
 * @param {number} gap    - Gap between cards (default 0.2)
 */
function hCardRow(n, cardHeight, gap = 0.2) {
  const totalGap = (n - 1) * gap;
  const w = (W - 2 * MX - totalGap) / n;
  const y = centerGroupY(cardHeight);
  return Array.from({ length: n }, (_, i) => ({
    x: MX + i * (w + gap), y, w, h: cardHeight,
  }));
}

// Example — 3 cards, each 3.5in tall:
const cards = hCardRow(3, 3.5);
cards.forEach((c, i) => {
  card(slide, c.x, c.y, c.w, c.h, items[i].color);
  // add content using c.x, c.y as origin
});
```

### `vStack()` — vertical stack of cards or blocks

Renders a vertical list of cards/blocks with consistent gaps, centered as a group.

```js
/**
 * Lay out items in a vertical stack, centered in content area.
 * @param {Array}  items   - Each: { h } — height of that block
 * @param {number} gap     - Gap between items (default 0.18)
 * Returns array of { y, h } for each item.
 */
function vStack(items, gap = 0.18) {
  const totalH = items.reduce((s, it) => s + it.h, 0) + gap * (items.length - 1);
  let y = centerGroupY(totalH);
  return items.map(it => {
    const entry = { y, h: it.h };
    y += it.h + gap;
    return entry;
  });
}

// Example — 3 KPI cards of varying heights stacked vertically on the right column:
const kpiItems = [{ h: 1.6 }, { h: 1.6 }, { h: 1.6 }];
const positions = vStack(kpiItems);
positions.forEach((pos, i) => {
  card(slide, RX, pos.y, RW, pos.h, kpis[i].color);
});
```

### `reserveBottom()` — leave room for a bottom banner

When a slide has a bottom note/banner, reduce the available height before calling `centerGroupY()`.

```js
/**
 * Returns effective FY when a bottom banner of height `bannerH` is present.
 * Use this as a replacement for FY when computing centerGroupY.
 */
function effectiveFY(bannerH, gap = 0.12) {
  return FY - bannerH - gap;
}

// Example — slide with a 0.37in bottom banner:
const EFY = effectiveFY(0.37);
function centerGroupY(groupH, topBias = 0.1) {
  const available = EFY - CONTENT_Y;  // use EFY instead of FY here
  return CONTENT_Y + Math.max(0, (available - groupH) / 2) - topBias;
}
```

---

## Common Layouts

### N-Column Cards — use `hCardRow()`

```js
// ✅ Correct — height driven by content
const itemH = 0.56;  // height per bullet row
const CH = cardH([itemH, itemH, itemH, itemH], { headerH: 0.55 });
const cols = hCardRow(3, CH, 0.2);  // 3 columns
cols.forEach((c, i) => {
  card(slide, c.x, c.y, c.w, c.h, items[i].color);
  // add text using c.x, c.y as origin
});

// ❌ Wrong — never do this
const CH = FY - CONTENT_Y - 0.12;  // hardcoded to fill slide
```

**Standard column gaps:**
- 3 columns: `gap = 0.2`
- 4 columns: `gap = 0.15`
- 5 columns: `gap = 0.18`
- 6 columns: `gap = 0.15`

### Two-Column Split

```js
const COL1_W = 5.4;
const COL2_X = MX + COL1_W + 0.4;
const COL2_W = W - COL2_X - MX + 0.1;

// Compute heights independently, then find shared Y using the taller column:
const CH_left  = cardH([...leftRows], { headerH: 0.55 });
const CH_right = cardH([...rightRows], { headerH: 0.55 });
const CH = Math.max(CH_left, CH_right);   // align tops, use taller for centering
const CY = centerGroupY(CH);

card(slide, MX,     CY, COL1_W, CH_left,  accentLeft);
card(slide, COL2_X, CY, COL2_W, CH_right, accentRight);
```

### Closing Slide

Full navy background with colored accent bars next to takeaways:

```js
function makeClosingSlide(pres, presTitle, heading, takeaways) {
  const slide = pres.addSlide();
  slide.addShape("rect", { x:0, y:0, w:W, h:H, fill:{color:C.navy}, line:{color:C.navy} });
  // Decorative circles right side
  slide.addShape("ellipse", { x:7.205, y:0.925, w:6.5, h:6.5, fill:{color:"1E3A7A", transparency:55}, line:{color:"1E3A7A"} });
  slide.addText(heading, { x:MX, y:1.0, w:7, h:0.72, fontSize:36, bold:true, color:C.white, fontFace:"Calibri" });
  slide.addShape("rect", { x:MX, y:1.82, w:2.8, h:0.04, fill:{color:C.orange}, line:{color:C.orange} });
  const colors = [C.orange, C.lblue, C.warmOr];
  takeaways.forEach((t, i) => {
    const py = 2.1 + i*0.73;
    slide.addShape("rect", { x:MX, y:py+0.1, w:0.05, h:0.38, fill:{color:colors[i%3]}, line:{color:colors[i%3]} });
    slide.addText(t, { x:MX+0.2, y:py, w:8.0, h:0.58, fontSize:14, color:C.white, fontFace:"Calibri", valign:"middle" });
  });
  footer(slide, presTitle);
}
```

---

## Full Script Structure

```js
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const SKILL_ASSETS = "/mnt/skills/user/artelys-pptx/assets";
// ... brand constants, logo loading, helpers above ...

const PRES_TITLE = "My Presentation";
const DATE = new Date().toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" });

async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title  = PRES_TITLE;
  pres.author = "Artelys";
  pres.company = "Artelys";

  makeTitleSlide(pres, ...);
  // ... other slides
  
  await pres.writeFile({ fileName: "output.pptx" });
  console.log("Done → output.pptx");
}
build().catch(console.error);
```

---

## QA

After generating, always convert and visually inspect:

```bash
python /mnt/skills/public/pptx/scripts/office/soffice.py --headless --convert-to pdf output.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 130 output.pdf slide
ls "$PWD"/slide-*.jpg
```

Then view each slide image. Check for:
- Logo visible in footer (white on dark — always use `LOGO_WHITE` in footer)
- Content fills the slide width (no blank right margin — means wrong dimensions)
- Text not too small (minimum 12pt for body, 14pt preferred)
- No content overflowing the footer

**Known LibreOffice rendering quirk**: text positioned with `valign:"top"` in large text boxes may appear anchored to bottom in PDF preview. This is a LibreOffice artifact — in PowerPoint the text renders at top as intended.

---

## Design Principles

- **Lean slides**: fewer items, bigger text. Prefer 3-4 bullet points over 6-8.
- **Minimum font sizes**: body 13pt, labels 11pt, captions 8pt. Never go below.
- **Content-driven card heights**: use `cardH()` to compute height from content, then `centerGroupY()` to place the group. **Never use `CH = FY - CONTENT_Y - constant`** — this creates blank white space when content is short and overflow when content is long.
- **Center content vertically**: cards and groups should sit centered in the available space, not anchored to the top or stretched to the footer.
- **Bottom banners reduce available height**: if a slide has a note/banner at the bottom, use `effectiveFY(bannerH)` before calling `centerGroupY()`.
- **White logo in footer and on dark backgrounds**, navy logo on white/light backgrounds.
- **Color variety**: use the full palette (navy, orange, lblue, pink, warmOr) across cards/accents — don't use only navy.
- **Always add a closing slide** with key takeaways unless the user says otherwise.

---

## Reference Files

- `assets/logo_b64.txt` — Artelys navy logo as base64 PNG
- `assets/logo_white_b64.txt` — Artelys white logo as base64 PNG  
- `assets/template_example.js` — Complete working 5-slide example deck (title, section, KPI cards, content+chart, timeline)
