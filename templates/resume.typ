// Single-column, ATS-friendly resume. Data comes from draft.yaml via --input data=/<path from root>.
// Layout is owned by this file and scripts/build.py; drafts only supply content and `keywords`.
// Knobs (set by build.py's auto-fit, never by hand): size (pt), lead (em), gap (em). preview=1 adds a draft footer.
#let d = yaml(sys.inputs.data)
#let size = float(sys.inputs.at("size", default: "10.5")) * 1pt
#let lead = float(sys.inputs.at("lead", default: "0.6")) * 1em
#let gap = float(sys.inputs.at("gap", default: "0.8")) * 1em
#let preview = sys.inputs.at("preview", default: "0") == "1"
// Personal look: fonts, which info is monospaced, accent color. build.py passes main/resume-style.yaml if it
// exists, else templates/style.default.yaml. Missing keys fall back to the defaults below.
#let st = yaml(sys.inputs.at("style", default: "/templates/style.default.yaml"))
#let body-font = st.at("body_font", default: ("Helvetica Neue", "Helvetica", "Arial"))
#let mono-font = st.at("mono_font", default: ("Menlo", "Courier New"))
#let mono-for = st.at("mono_for", default: ())
#let mono-scale = float(st.at("mono_scale", default: 0.9))
#let muted = rgb(st.at("muted", default: "#555555"))
#let accent = rgb(st.at("accent", default: "#1f3a5f"))
// m("dates", x): monospaced if the style says so for this kind of info (contact, dates, skills, tagline).
#let m(kind, x, k: 1) = if kind in mono-for { text(font: mono-font, size: size * mono-scale * k, x) } else if k != 1 { text(size: size * k, x) } else { x }

#set page(
  paper: "us-letter",
  margin: (x: 0.6in, y: 0.5in),
  footer: if preview { align(center, text(size: 7pt, fill: muted)[DRAFT preview, not approved]) },
)
#set text(font: body-font, size: size, hyphenate: false)
#set par(justify: false, leading: lead, spacing: lead)
#set list(marker: text(fill: muted)[•], indent: 0.2em, body-indent: 0.55em, spacing: lead)

// Bold each keyword (exact text match, no regex). Used on summary and bullets only.
#let hl(body) = {
  let out = [#body]
  for k in d.at("keywords", default: ()) {
    out = {
      show k: it => text(weight: "bold", it)
      out
    }
  }
  out
}

// A bullet with invisible start/end markers so build.py can count its lines and spot a short last line.
#let mark(kind, b) = context [#metadata((kind: kind, id: b.at("source", default: ""), pos: here().position(), w: measure(hl(b.text)).width, size: text.size)) <bl>]
#let bullet(b) = [#mark("s", b)#hl(b.text)#mark("e", b)]

#let section(title) = {
  v(gap)
  text(size: size * 1.05, weight: "bold", fill: accent, tracking: 0.06em)[#upper(title)]
  v(-0.55em)
  line(length: 100%, stroke: 0.6pt + accent)
  v(0.15em)
}

#let entry(left, right, sub: none) = {
  grid(columns: (1fr, auto), column-gutter: 1em, left, text(fill: muted)[#m("dates", right)])
  if sub != none and sub != "" { v(-0.35em); text(style: "italic", fill: muted, size: size * 0.95)[#sub] }
}

// ---------- header ----------
#align(center)[
  #text(size: 20pt, weight: "bold")[#d.header.name]
  #v(-0.4em)
  // contact always stays on one line: shrink it (never below 8pt) if it would wrap
  #layout(region => {
    let line = d.header.contact.join("  ·  ")
    let draw(k) = text(fill: muted)[#m("contact", line, k: 0.92 * k)]
    let w = measure(draw(1)).width
    let k = if w > region.width { calc.max(8pt / (size * 0.92), (region.width / w) * 0.98) } else { 1 }
    draw(k)
  })
]

#if "summary" in d and d.summary != none [
  #section("Summary")
  #hl(d.summary)
]

#section("Experience")
#for (i, e) in d.experience.enumerate() [
  #if i > 0 { v(gap * 0.6) }
  #entry([*#e.company* #h(0.3em)—#h(0.3em) #e.title], e.dates, sub: e.at("location", default: none))
  #for b in e.bullets [
    - #bullet(b)
  ]
]

#if "projects" in d and d.projects != none and d.projects.len() > 0 [
  #section("Projects")
  #for (i, p) in d.projects.enumerate() [
    #if i > 0 { v(gap * 0.6) }
    #entry([*#p.name*#if "tagline" in p [ #h(0.3em)—#h(0.3em) #m("tagline", p.tagline)]], p.at("dates", default: ""))
    #for b in p.bullets [
      - #bullet(b)
    ]
  ]
]

#section("Education")
#for e in d.education [
  #entry([*#e.school* #h(0.3em)—#h(0.3em) #e.degree], e.dates)
]

#section("Skills")
#if type(d.skills) == dictionary [
  #for (group, items) in d.skills [
    *#group:* #m("skills", items.join(", ")) \
  ]
] else [
  #m("skills", d.skills.join(", "))
]

// End marker: build.py reads its position to measure how full the page is.
#context [#metadata(here().position()) <end>]
