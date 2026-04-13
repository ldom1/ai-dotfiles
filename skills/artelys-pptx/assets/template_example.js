const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const C = {
  navy:   "#16469C", orange: "#F25924", lblue:  "#00AFF0",
  pink:   "#B72075", warmOr: "#F8933A", grey:   "#5B5B5B",
  lgrey:  "#F2F4F8", white:  "#FFFFFF", black:  "#1A1A1A", footer: "#0D2C6B",
};

const LOGO_NAVY_B64  = "data:image/png;base64," + fs.readFileSync(path.join(__dirname, "logo_b64.txt"), "utf8").trim();
const LOGO_WHITE_B64 = "data:image/png;base64," + fs.readFileSync(path.join(__dirname, "logo_white_b64.txt"), "utf8").trim();

// LAYOUT_WIDE = 13.33 × 7.5 inches
const W = 13.33;
const H = 7.5;
const FH = 0.42;
const FY = H - FH;
const F_LOGO_W = 1.85;
const F_LOGO_H = 0.23;
const MX = 0.55;

const PRES_TITLE = "Artelys Presentation Template";
const DATE = new Date().toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" });

function addFooter(slide, title) {
  slide.addShape("rect", { x:0, y:FY, w:W, h:FH, fill:{color:C.footer}, line:{color:C.footer} });
  slide.addImage({ data:LOGO_WHITE_B64, x:0.22, y:FY+(FH-F_LOGO_H)/2, w:F_LOGO_W, h:F_LOGO_H });
  slide.addText(title||PRES_TITLE, { x:F_LOGO_W+0.4, y:FY, w:W-F_LOGO_W-1.8, h:FH, fontSize:8.5, color:"AABBD4", align:"center", valign:"middle", fontFace:"Calibri" });
  slide.addText(DATE, { x:W-1.4, y:FY, w:1.2, h:FH, fontSize:8.5, color:"AABBD4", align:"right", valign:"middle", fontFace:"Calibri" });
}

function sectionLabel(slide, text, x, y, w, color) {
  slide.addText(text.toUpperCase(), { x, y, w, h:0.22, fontSize:8, bold:true, color:color||C.orange, fontFace:"Calibri", charSpacing:2 });
  slide.addShape("rect", { x, y:y+0.24, w:0.35, h:0.04, fill:{color:color||C.orange}, line:{color:color||C.orange} });
}

function makeTitleSlide(pres) {
  const slide = pres.addSlide();
  const PW = 5.0;
  slide.addShape("rect", { x:0, y:0, w:PW, h:H, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addShape("rect", { x:PW, y:0, w:0.08, h:H, fill:{color:C.orange}, line:{color:C.orange} });
  slide.addImage({ data:LOGO_WHITE_B64, x:0.42, y:0.48, w:3.6, h:0.45 });
  slide.addShape("ellipse", { x:3.2, y:5.0, w:2.4, h:2.4, fill:{color:"1E3A7A", transparency:40}, line:{color:"1E3A7A"} });
  slide.addShape("ellipse", { x:0.3, y:4.8, w:1.6, h:1.6, fill:{color:"0F2560", transparency:30}, line:{color:"0F2560"} });
  const RX = PW+0.55; const RW = W-RX-0.4;
  slide.addText("PRESENTATION TITLE", { x:RX, y:1.9, w:RW, h:0.85, fontSize:36, bold:true, color:C.navy, fontFace:"Calibri" });
  slide.addText("Subtitle or topic description goes here", { x:RX, y:2.9, w:RW, h:0.5, fontSize:16, color:C.grey, fontFace:"Calibri" });
  slide.addShape("rect", { x:RX, y:3.52, w:RW*0.72, h:0.03, fill:{color:C.orange}, line:{color:C.orange} });
  slide.addText([{text:"Author Name  •  ", options:{bold:true,color:C.black}},{text:DATE, options:{color:C.grey}}], { x:RX, y:3.7, w:RW, h:0.38, fontSize:13, fontFace:"Calibri" });
  slide.addShape("rect", { x:RX, y:4.25, w:1.7, h:0.34, fill:{color:C.lgrey}, line:{color:"C8D4E8", w:0.5} });
  slide.addText("CONFIDENTIAL", { x:RX, y:4.25, w:1.7, h:0.34, fontSize:8.5, bold:true, color:C.grey, align:"center", valign:"middle", fontFace:"Calibri", charSpacing:1 });
  addFooter(slide, PRES_TITLE);
}

function makeSectionSlide(pres, num, title, desc) {
  const slide = pres.addSlide();
  slide.addShape("rect", { x:0, y:0, w:W, h:H, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addShape("ellipse", { x:8.5, y:-0.5, w:6.0, h:6.0, fill:{color:"1E3A7A", transparency:55}, line:{color:"1E3A7A"} });
  slide.addShape("ellipse", { x:10.0, y:1.2, w:3.8, h:3.8, fill:{color:"122B6A", transparency:35}, line:{color:"122B6A"} });
  slide.addText(`0${num}`, { x:MX, y:1.5, w:1.6, h:1.4, fontSize:80, bold:true, color:C.orange, fontFace:"Calibri" });
  slide.addShape("rect", { x:MX, y:3.1, w:0.07, h:1.5, fill:{color:C.orange}, line:{color:C.orange} });
  slide.addText(title, { x:MX+0.25, y:3.05, w:8.0, h:0.95, fontSize:34, bold:true, color:C.white, fontFace:"Calibri" });
  slide.addText(desc, { x:MX+0.25, y:4.1, w:7.5, h:0.55, fontSize:15, color:"AABBDD", fontFace:"Calibri" });
  addFooter(slide, PRES_TITLE);
}

function makeKpiSlide(pres) {
  const slide = pres.addSlide();
  slide.addShape("rect", { x:0, y:0, w:W, h:0.09, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addText("Key Metrics", { x:MX, y:0.22, w:W-1.0, h:0.58, fontSize:28, bold:true, color:C.navy, fontFace:"Calibri" });
  sectionLabel(slide, "Overview", MX, 0.82, 4);

  const CARD_Y=1.35, CARD_H=5.58, CARD_W=3.8, GAP=0.22;
  const kpis = [
    { value:"87%",   label:"Optimization Efficiency", note:"+4.2% vs last year",    color:C.navy,   fill:0.87 },
    { value:"1,240", label:"Scenarios Computed",      note:"in the last 30 days",   color:C.orange, fill:0.65 },
    { value:"€2.3M", label:"Cost Savings Identified", note:"across all portfolios", color:C.lblue,  fill:0.72 },
  ];
  kpis.forEach((k, i) => {
    const cx = MX + i*(CARD_W+GAP);
    slide.addShape("rect", { x:cx+0.04, y:CARD_Y+0.04, w:CARD_W, h:CARD_H, fill:{color:"D0DAE8"}, line:{color:"D0DAE8"} });
    slide.addShape("rect", { x:cx, y:CARD_Y, w:CARD_W, h:CARD_H, fill:{color:C.lgrey}, line:{color:"D8E2EE", w:0.5} });
    slide.addShape("rect", { x:cx, y:CARD_Y, w:CARD_W, h:0.09, fill:{color:k.color}, line:{color:k.color} });
    slide.addText(k.value, { x:cx+0.25, y:CARD_Y+0.35, w:CARD_W-0.5, h:1.1, fontSize:54, bold:true, color:k.color, fontFace:"Calibri" });
    slide.addText(k.label, { x:cx+0.25, y:CARD_Y+1.55, w:CARD_W-0.5, h:0.52, fontSize:15, bold:true, color:C.black, fontFace:"Calibri" });
    slide.addText(k.note,  { x:cx+0.25, y:CARD_Y+2.12, w:CARD_W-0.5, h:0.4,  fontSize:12, color:C.grey, fontFace:"Calibri", italic:true });
    const barY = CARD_Y+CARD_H-0.65;
    slide.addShape("rect", { x:cx+0.25, y:barY, w:CARD_W-0.5, h:0.28, fill:{color:"D0DAE8"}, line:{color:"D0DAE8"} });
    slide.addShape("rect", { x:cx+0.25, y:barY, w:(CARD_W-0.5)*k.fill, h:0.28, fill:{color:k.color, transparency:15}, line:{color:k.color} });
    slide.addText(`${Math.round(k.fill*100)}%`, { x:cx+0.25, y:barY+0.3, w:CARD_W-0.5, h:0.22, fontSize:8.5, color:C.grey, fontFace:"Calibri" });
  });
  addFooter(slide, PRES_TITLE);
}

function makeContentChartSlide(pres) {
  const slide = pres.addSlide();
  slide.addShape("rect", { x:0, y:0, w:W, h:0.09, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addText("Analysis Results", { x:MX, y:0.22, w:W-1.0, h:0.58, fontSize:28, bold:true, color:C.navy, fontFace:"Calibri" });
  sectionLabel(slide, "Detailed breakdown", MX, 0.82, 5);

  const COL1_W=5.4, COL_Y=1.38;
  const points = [
    { color:C.navy,   text:"Optimization converged in 94% of test cases, exceeding the 90% target." },
    { color:C.orange, text:"Average solve time reduced by 31% through warm-start initialization." },
    { color:C.lblue,  text:"Constraint violation rate dropped below 0.5% across all scenarios." },
    { color:C.pink,   text:"Scalability validated on instances up to 10× baseline complexity." },
  ];
  points.forEach((p, i) => {
    const py = COL_Y + i*0.95;
    slide.addShape("ellipse", { x:MX, y:py+0.05, w:0.36, h:0.36, fill:{color:p.color}, line:{color:p.color} });
    slide.addText("▶", { x:MX, y:py+0.05, w:0.36, h:0.36, fontSize:10, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri" });
    slide.addText(p.text, { x:MX+0.48, y:py, w:COL1_W-0.48, h:0.72, fontSize:13, color:C.black, fontFace:"Calibri", valign:"top" });
  });

  const COL2_X=MX+COL1_W+0.4, CHART_W=W-COL2_X-0.3, CHART_Y=1.28, CHART_H=FY-1.28-0.18;
  slide.addShape("rect", { x:COL2_X, y:CHART_Y, w:CHART_W, h:CHART_H, fill:{color:C.lgrey}, line:{color:"D8E2EE", w:0.5} });
  slide.addText("Convergence Rate by Scenario (%)", { x:COL2_X+0.18, y:CHART_Y+0.1, w:CHART_W-0.36, h:0.3, fontSize:10.5, bold:true, color:C.navy, fontFace:"Calibri" });

  const chartData = [
    {name:"Scenario A", val:87},{name:"Scenario B", val:73},{name:"Scenario C", val:91},
    {name:"Scenario D", val:65},{name:"Scenario E", val:82},
  ];
  const barColors=[C.navy,C.orange,C.lblue,C.pink,C.warmOr];
  const LABEL_W=1.22, BAR_X=COL2_X+0.18+LABEL_W+0.1, BAR_MAX_W=CHART_W-LABEL_W-0.75;
  const BAR_START_Y=CHART_Y+0.55, BAR_H_EACH=(CHART_H-0.8)/chartData.length-0.12;

  chartData.forEach((d, i) => {
    const by=BAR_START_Y+i*(BAR_H_EACH+0.12), bw=BAR_MAX_W*d.val/100;
    slide.addText(d.name, { x:COL2_X+0.18, y:by, w:LABEL_W, h:BAR_H_EACH, fontSize:10, color:C.grey, valign:"middle", align:"right", fontFace:"Calibri" });
    slide.addShape("rect", { x:BAR_X, y:by+0.05, w:BAR_MAX_W, h:BAR_H_EACH-0.1, fill:{color:"DDE4EE"}, line:{color:"DDE4EE"} });
    slide.addShape("rect", { x:BAR_X, y:by+0.05, w:bw, h:BAR_H_EACH-0.1, fill:{color:barColors[i]}, line:{color:barColors[i]} });
    slide.addText(`${d.val}%`, { x:BAR_X+bw+0.06, y:by, w:0.55, h:BAR_H_EACH, fontSize:10, bold:true, color:barColors[i], valign:"middle", fontFace:"Calibri" });
  });
  addFooter(slide, PRES_TITLE);
}

function makeTimelineSlide(pres) {
  const slide = pres.addSlide();
  slide.addShape("rect", { x:0, y:0, w:W, h:0.09, fill:{color:C.navy}, line:{color:C.navy} });
  slide.addText("Project Roadmap", { x:MX, y:0.22, w:W-1.0, h:0.58, fontSize:28, bold:true, color:C.navy, fontFace:"Calibri" });
  sectionLabel(slide, "Milestones & Deliverables", MX, 0.82, 6);

  const phases = [
    { label:"Phase 1", title:"Requirements", desc:"Stakeholder interviews, functional spec, data audit",   color:C.navy   },
    { label:"Phase 2", title:"Design",        desc:"Architecture design, algorithm selection, prototype",    color:C.orange },
    { label:"Phase 3", title:"Development",   desc:"Core implementation, unit & integration tests",         color:C.lblue  },
    { label:"Phase 4", title:"Validation",    desc:"Acceptance tests, benchmarks, UAT sign-off",            color:C.pink   },
  ];
  const COL_W=(W-2*MX)/phases.length, NODE_Y=2.5, NODE_D=0.42;
  slide.addShape("rect", { x:MX+NODE_D/2, y:NODE_Y+NODE_D/2-0.025, w:W-2*MX-NODE_D, h:0.05, fill:{color:"C0CEDE"}, line:{color:"C0CEDE"} });

  phases.forEach((p, i) => {
    const cx=MX+i*COL_W, nodeX=cx+COL_W/2-NODE_D/2;
    slide.addText(p.label, { x:cx, y:NODE_Y-0.45, w:COL_W, h:0.32, fontSize:10, bold:true, color:p.color, align:"center", fontFace:"Calibri" });
    slide.addShape("ellipse", { x:nodeX, y:NODE_Y, w:NODE_D, h:NODE_D, fill:{color:p.color}, line:{color:p.color} });
    slide.addText(`${i+1}`, { x:nodeX, y:NODE_Y, w:NODE_D, h:NODE_D, fontSize:14, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri" });
    const CARD_X=cx+0.12, CARD_W=COL_W-0.24, CARD_Y=NODE_Y+NODE_D+0.25, CARD_H=FY-CARD_Y-0.22;
    slide.addShape("rect", { x:CARD_X, y:CARD_Y, w:CARD_W, h:CARD_H, fill:{color:C.lgrey}, line:{color:"D0DAE8", w:0.5} });
    slide.addShape("rect", { x:CARD_X, y:CARD_Y, w:CARD_W, h:0.07, fill:{color:p.color}, line:{color:p.color} });
    slide.addText(p.title, { x:CARD_X+0.15, y:CARD_Y+0.12, w:CARD_W-0.3, h:0.44, fontSize:14, bold:true, color:p.color, fontFace:"Calibri" });
    slide.addText(p.desc,  { x:CARD_X+0.15, y:CARD_Y+0.6,  w:CARD_W-0.3, h:CARD_H-0.8, fontSize:11.5, color:C.grey, fontFace:"Calibri" });
  });
  addFooter(slide, PRES_TITLE);
}

async function build() {
  const pres = new pptxgen();
  pres.layout="LAYOUT_WIDE"; pres.title=PRES_TITLE; pres.author="Artelys"; pres.company="Artelys";
  makeTitleSlide(pres);
  makeSectionSlide(pres, 1, "Context & Objectives", "Setting the scene and defining the scope of analysis");
  makeKpiSlide(pres);
  makeContentChartSlide(pres);
  makeTimelineSlide(pres);
  await pres.writeFile({ fileName: "artelys_example_deck.pptx" });
  console.log("Done → artelys_example_deck.pptx");
}
build().catch(console.error);
