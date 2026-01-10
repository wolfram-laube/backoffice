// =============================================================================
// BLAUWEISS-EDV LLC – Service Report / Leistungsnachweis
// =============================================================================

// === DATA (will be replaced) ===
#let report_nr = "SR-2026-001"
#let report_date = "January 10, 2026"
#let period = "January 2026"
#let project_nr = "PRJ-001"

#let customer_name = "Example Company"
#let customer_address = "Street 123"
#let customer_city = "12345 City"
#let customer_country = "Germany"

#let consultant_name = "Wolfram Laube"
#let consultant_role = "IT Consultant / Software Architect"

// entries: (date, hours, description)
#let entries = (
  ("2026-01-06", 8.0, "Example work"),
)

#let hourly_rate = 105.00

// === COLORS ===
#let blue = rgb("#1e5a99")
#let green = rgb("#8dc63f")
#let light_gray = rgb("#f5f5f5")

// === PAGE SETUP ===
#set page(
  paper: "a4",
  margin: (top: 1.5cm, bottom: 1.5cm, left: 2cm, right: 1.5cm),
  footer: [
    #set text(size: 8pt, fill: gray)
    #line(length: 100%, stroke: 0.5pt + gray)
    #v(3pt)
    #grid(
      columns: (1fr, 1fr),
      align: (left, right),
      [Service Report #report_nr],
      [Page #counter(page).display() of #locate(loc => counter(page).final(loc).first())],
    )
  ]
)

#set text(font: "Space Grotesk", size: 9pt)

// === HEADER ===
#grid(
  columns: (1fr, auto),
  gutter: 1cm,
  [
    #image("logo-blauweiss.png", width: 5cm)
  ],
  [
    #align(right)[
      #text(size: 18pt, fill: blue, weight: "bold")[SERVICE REPORT]
      #v(0.2cm)
      #text(size: 10pt)[#report_nr]
      #v(0.1cm)
      #text(size: 9pt, fill: gray)[#report_date]
    ]
  ]
)

#v(0.3cm)
#line(length: 100%, stroke: 1pt + blue)
#v(0.3cm)

// === INFO GRID ===
#grid(
  columns: (1fr, 1fr),
  gutter: 1cm,
  [
    #text(size: 8pt, fill: blue, weight: "bold")[CLIENT]
    #v(0.1cm)
    #strong[#customer_name]
    #linebreak()
    #customer_address
    #linebreak()
    #customer_city
    #linebreak()
    #customer_country
  ],
  [
    #text(size: 8pt, fill: blue, weight: "bold")[PROJECT DETAILS]
    #v(0.1cm)
    #grid(
      columns: (auto, 1fr),
      gutter: 0.5cm,
      row-gutter: 0.2cm,
      [Project Nr:], [#strong[#project_nr]],
      [Period:], [#strong[#period]],
      [Consultant:], [#consultant_name],
      [Role:], [#consultant_role],
    )
  ]
)

#v(0.4cm)

// === TIME ENTRIES TABLE ===
#let total_hours = entries.map(e => e.at(1)).sum()
#let total_amount = total_hours * hourly_rate

#text(size: 8pt, fill: blue, weight: "bold")[TIME ENTRIES]
#v(0.2cm)

#table(
  columns: (auto, auto, 1fr),
  align: (center, right, left),
  stroke: 0.5pt + rgb("#ddd"),
  inset: 6pt,
  fill: (col, row) => if row == 0 { light_gray } else { none },
  
  // Header
  [*Date*], [*Hours*], [*Description*],
  
  // Entries
  ..entries.map(e => (
    e.at(0),
    [#e.at(1) h],
    e.at(2),
  )).flatten(),
)

#v(0.3cm)

// === SUMMARY ===
#align(right)[
  #box(
    fill: light_gray,
    inset: 10pt,
    radius: 3pt,
  )[
    #grid(
      columns: (auto, auto),
      gutter: 1cm,
      align: (left, right),
      [Total Hours:], [*#total_hours h*],
      [Hourly Rate:], [EUR #hourly_rate],
      [*Total Amount:*], [*EUR #calc.round(total_amount, digits: 2)*],
    )
  ]
]

#v(0.5cm)

// === SIGNATURES ===
#line(length: 100%, stroke: 0.5pt + gray)
#v(0.3cm)

#grid(
  columns: (1fr, 1fr),
  gutter: 2cm,
  [
    #text(size: 8pt, fill: blue, weight: "bold")[CONSULTANT SIGNATURE]
    #v(1cm)
    #line(length: 80%, stroke: 0.5pt + gray)
    #v(0.1cm)
    #text(size: 8pt, fill: gray)[#consultant_name / Date]
  ],
  [
    #text(size: 8pt, fill: blue, weight: "bold")[CLIENT APPROVAL]
    #v(1cm)
    #line(length: 80%, stroke: 0.5pt + gray)
    #v(0.1cm)
    #text(size: 8pt, fill: gray)[Name / Date]
  ]
)

#v(0.3cm)

#text(size: 8pt, fill: gray)[
  This service report confirms the hours worked as listed above. 
  By signing, both parties acknowledge the accuracy of the recorded time entries.
]
