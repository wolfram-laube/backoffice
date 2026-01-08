// =============================================================================
// BLAUWEISS-EDV LLC – Rechnung OP_AR010_2025
// Generated 2025-12-19 14:32
// Region: EU (Reverse Charge) | Language: Deutsch
// =============================================================================

// === DATA ===
#let invoice_nr = "OP_AR010_2025"
#let invoice_date = "19. Dezember 2025"
#let project_nr = "00003151"
#let currency = "EUR"

// Customer
#let customer_name = "nemensis AG Deutschland"
#let customer_address = "Alter Wall 69"
#let customer_city = "D - 20457 Hamburg"
#let customer_country = "Germany"
#let customer_reg = "HRB. NR.: 181535 Hamburg"
#let customer_vat = "DE310161615"

// Line items
#let items = (
  ("Beratungsleistung remote", 184.00, "Ph", 105.00),
)

// === COMPANY DATA ===
#let company_name = "BLAUWEISS-EDV LLC"
#let company_address = "106 Stratford St"
#let company_city = "Houston, TX 77006"
#let company_country = "USA"
#let company_phone = "+1 832 517 1100"
#let company_email = "info@blauweiss-edv.com"
#let company_web = "www.blauweiss-edv.com"

// Bank
#let bank_name = "Raiba St. Florian/Schärding"
#let bank_iban = "AT46 2032 6000 0007 0623"
#let bank_bic = "RZOOAT2L522"
#let bank_note = "Zahlungen treuhänderisch an M. Matejka bis Eröffnung US-Firmenkontos"

// === COLORS ===
#let cyan = rgb("#00b4d8")
#let light_cyan = rgb("#e0f7fa")

// === PAGE SETUP ===
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 3cm, left: 2cm, right: 1.5cm),
  footer: [
    #set text(size: 8pt, fill: gray)
    #line(length: 100%, stroke: 0.5pt + gray)
    #v(3pt)
    #grid(
      columns: (1fr, 1fr, 1fr),
      align: (left, center, right),
      [#bank_name | BIC: #bank_bic],
      [IBAN: #bank_iban],
      [#company_web],
    )
  ]
)

#set text(font: "Inter", size: 10pt)

// === HEADER ===
#grid(
  columns: (1fr, auto),
  gutter: 1cm,
  [#image("logo-blauweiss.png", width: 6cm)],
  [
    #box(fill: light_cyan, inset: 10pt, radius: 3pt)[
      #set text(size: 9pt)
      #strong[#company_name]
      
      #company_address \\
      #company_city \\
      #company_country
      
      #v(0.3cm)
      #text(fill: cyan)[#company_phone] \\
      #text(fill: cyan)[#company_email]
    ]
  ]
)

#v(1cm)

// === CUSTOMER ===
#customer_name \\
#customer_address \\
#customer_city \\
#customer_country \\
#customer_reg \\
USt-IdNr.: DE310161615

#v(1cm)

// === TITLE ===
#grid(
  columns: (auto, auto),
  gutter: 2cm,
  [#strong[Rechnung:] #text(fill: cyan)[#invoice_nr]],
  [#strong[Datum:] #text(fill: cyan)[#invoice_date]],
)

#v(0.5cm)

// === BANK NOTICE ===
#box(width: 100%, fill: rgb("#fff3cd"), inset: 8pt, radius: 3pt)[
  #text(size: 9pt)[
    *ACHTUNG!* Bitte berücksichtigen Sie die Bankverbindung: IBAN #bank_iban \\
    #text(size: 8pt, fill: gray)[#bank_note]
  ]
]

#v(0.5cm)

// === LETTER ===
Sehr geehrte Damen und Herren!

Bezugnehmend auf den Projektvertrag Nr. #strong[#project_nr] erlauben wir uns folgende Positionen in Rechnung zu stellen:

#box(width: 100%, fill: rgb("#f0f0f0"), inset: 8pt, radius: 3pt)[
  #text(size: 9pt)[
    *Hinweis zur Umsatzsteuer:* Reverse Charge gem. Art. 196 der Richtlinie 2006/112/EG – MwStSystRL
  ]
]

#v(0.5cm)

// === TABLE ===
#let total = items.map(p => p.at(1) * p.at(3)).sum()

#table(
  columns: (2fr, 1fr, 1fr, 1fr),
  align: (left, right, right, right),
  stroke: 0.5pt + gray,
  inset: 8pt,
  table.header([*Beschreibung*], [*Menge*], [*Einzelpreis*], [*Betrag*]),
  ..items.map(p => {
    let amt = p.at(1) * p.at(3)
    (p.at(0), [#p.at(1) #p.at(2)], [#currency #str(p.at(3))], [#currency #str(calc.round(amt, digits: 2))])
  }).flatten(),
  table.cell(colspan: 3, align: right)[*Gesamt (netto)*],
  [*#currency #str(calc.round(total, digits: 2))*],
)

#v(0.3cm)

#text(size: 9pt, fill: gray)[
  Kein Ausweis von Umsatzsteuer – Leistungsempfänger schuldet die Steuer \\
  USt-IdNr.: DE310161615
]

#v(0.5cm)

Wir bedanken uns für das Vertrauen und die gute Zusammenarbeit.

- 3% Skonto bei Sofortzahlung (1-2 Tage)

#v(1cm)

Mit freundlichen Grüßen,

#v(1.5cm)

#line(length: 5cm, stroke: 0.5pt + gray)
#text(size: 8pt, fill: gray)[Autorisierte Unterschrift]

#v(0.5cm)

*Anlage:*
- Leistungsschein
- Digitale Signatur
