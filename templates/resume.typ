// Single-column, ATS-friendly resume. Data comes from draft.yaml via --input data=/<path from root>.
// Layout is owned by this file and scripts/build.py; drafts only supply content and `keywords`.
// Knobs (set by build.py's auto-fit, never by hand): size (pt), lead (em), gap (em). preview=1 adds a draft footer.
#let d = yaml(sys.inputs.data)
#let size = float(sys.inputs.at("size", default: "10")) * 1pt
#let lead = float(sys.inputs.at("lead", default: "0.6")) * 1em
#let gap0 = float(sys.inputs.at("gap", default: "0.8")) * 1em
#let preview = sys.inputs.at("preview", default: "0") == "1"
// Look: a preset from templates/styles/ (`base:`, default traditional) overlaid with main/resume-style.yaml if it exists.
// Missing keys fall back to the defaults below.
#let user-style = yaml(sys.inputs.at("style", default: "/templates/styles/traditional.yaml"))
#let st = yaml("/templates/styles/" + user-style.at("base", default: "traditional") + ".yaml") + user-style
#let body-font = st.at("body_font", default: ("Helvetica Neue", "Helvetica", "Arial"))
#let mono-font = st.at("mono_font", default: ("Menlo", "Courier New"))
#let mono-for = st.at("mono_for", default: ())
#let mono-scale = float(st.at("mono_scale", default: 0.9))
#let muted = rgb(st.at("muted", default: "#555555"))
#let accent = rgb(st.at("accent", default: "#1f3a5f"))
#let ink = rgb(st.at("text_color", default: "#000000"))
#let display-font = { let f = st.at("display_font", default: ()); if f == none or f.len() == 0 { body-font } else { f } }       // name + section headings
#let display-weight = if st.at("display_bold", default: true) { "bold" } else { "regular" }
#let head-color = rgb(st.at("heading_color", default: st.at("accent", default: "#1f3a5f")))
#let head-upper = st.at("heading_case", default: "upper") == "upper"
#let head-track = float(st.at("heading_tracking", default: 0.06)) * 1em
#let rule-style = st.at("rule", default: "solid")                   // solid | dashed | none
#let rule-color = rgb(st.at("rule_color", default: st.at("accent", default: "#1f3a5f")))
#let air = float(st.at("spacing", default: 1.0))
#let gap = gap0 * air      // personal taste: more or less air between blocks
#let rails = st.at("rails", default: false)                         // vertical lines just outside the text edges
#let rail-dash = if st.at("rail_style", default: "dashed") == "dashed" { "dashed" } else { none }
#let rail-color = rgb(st.at("rail_color", default: "#d2d2d2"))
#let rail-inset = 8pt                                               // rail distance outside the text column
#let rule-full = st.at("rule_span", default: "text") == "page"     // heading rules run edge to edge
#let joints = rails and st.at("joints", default: false)            // small circles where rules cross rails
#let joint-r = float(st.at("joint_radius", default: 1.8)) * 1pt
// m("dates", x): monospaced if the style says so for this kind of info (contact, dates, skills, tagline).
#let m(kind, x, k: 1) = if kind in mono-for { text(font: mono-font, size: size * mono-scale * k, x) } else if k != 1 { text(size: size * k, x) } else { x }

#set page(
  paper: "us-letter",
  margin: (x: 0.6in, y: 0.5in),
  background: if rails {
    let st = (paint: rail-color, thickness: 0.6pt, dash: rail-dash)
    place(left + top, dx: 0.6in - rail-inset, line(angle: 90deg, length: 100%, stroke: st))
    place(right + top, dx: -0.6in + rail-inset, line(angle: 90deg, length: 100%, stroke: st))
  },
  footer: if preview { align(center, text(size: 7pt, fill: muted)[DRAFT preview, not approved]) },
)
#set text(font: body-font, size: size, hyphenate: false, fill: ink)
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
  text(font: display-font, size: size * 1.05, weight: display-weight, fill: head-color, tracking: head-track)[#if head-upper { upper(title) } else { title }]
  if rule-style != "none" {
    v(-0.55em + 0.2em * (air - 1))
    let stroke = (paint: rule-color, thickness: 0.6pt, dash: if rule-style == "dashed" { "dashed" } else { none })
    if rule-full {
      // zero-height box: the rule spills into the side margins to the page edges
      box(width: 100%, height: 0.6pt, {
        place(left, dx: -0.6in, line(length: 100% + 1.2in, stroke: stroke))
        if joints {
          for x in (-rail-inset, 100% + rail-inset) {
            place(left, dx: x - joint-r, dy: -joint-r + 0.3pt,
              circle(radius: joint-r, fill: white, stroke: (paint: rule-color, thickness: 0.6pt)))
          }
        }
      })
    } else {
      line(length: 100%, stroke: stroke)
    }
  }
  v(0.15em + 0.35em * (air - 1))
}

#let entry(left, right, sub: none) = {
  grid(columns: (1fr, auto), column-gutter: 1em, left, text(fill: muted)[#m("dates", right)])
  if sub != none and sub != "" { v(-0.35em); text(style: "italic", fill: muted, size: size * 0.95)[#sub] }
}

// ---------- header ----------
#align(center)[
  #text(font: display-font, size: 20pt, weight: display-weight)[#d.header.name]
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
  #bullet((text: d.summary, source: "summary"))   // markers let build.py check the summary too
]

#section("Experience")
#for (i, e) in d.experience.enumerate() [
  #if i > 0 { v(gap * 0.6 * air) }
  #entry([*#e.company* #h(0.3em)—#h(0.3em) #e.title], e.dates, sub: e.at("location", default: none))
  #for b in e.bullets [
    - #bullet(b)
  ]
]

#if "projects" in d and d.projects != none and d.projects.len() > 0 [
  #section("Projects")
  #for (i, p) in d.projects.enumerate() [
    #if i > 0 { v(gap * 0.6 * air) }
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
