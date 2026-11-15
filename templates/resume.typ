// Single-column, ATS-friendly resume. Data comes from draft.yaml via --input data=<path>.
#let d = yaml(sys.inputs.data)
#set page(margin: (x: 0.7in, y: 0.6in), paper: "us-letter")
#set text(font: "Helvetica", size: 10pt)
#set par(justify: false, leading: 0.55em)
#show heading.where(level: 2): it => [
  #v(0.6em)
  #text(size: 11pt, weight: "bold")[#upper(it.body)]
  #v(-0.5em)
  #line(length: 100%, stroke: 0.5pt)
]

#align(center)[
  #text(size: 18pt, weight: "bold")[#d.header.name] \
  #d.header.contact.join("  |  ")
]

#if "summary" in d [
  == Summary
  #d.summary
]

== Experience
#for e in d.experience [
  *#e.company* — #e.title #h(1fr) #e.dates \
  #if "location" in e [#emph[#e.location]]
  #for b in e.bullets [
    - #b.text
  ]
]

#if "projects" in d [
  == Projects
  #for p in d.projects [
    *#p.name* #if "dates" in p [#h(1fr) #p.dates]
    #for b in p.bullets [
      - #b.text
    ]
  ]
]

== Education
#for e in d.education [
  *#e.school* — #e.degree #h(1fr) #e.dates \
]

== Skills
#d.skills.join(", ")
