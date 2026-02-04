// BLAUWEISS Invoice Template - German (Rechnung)
// Usage: typst compile rechnung-de.typ --input data.json

#let invoice(
  invoice_number: "AR_001_2026",
  invoice_date: "03. Januar 2026",
  client_name: "Kunde GmbH",
  client_address: "Musterstraße 123",
  client_city: "D - 12345 Musterstadt",
  client_reg_id: "",
  client_vat_id: "",
  contract_number: "00003151",
  remote_hours: 0,
  remote_rate: 105,
  onsite_hours: 0,
  onsite_rate: 120,
  logo_path: "logo.jpg",
) = {
  // Colors
  let bw_blue = rgb("#00aeef")
  let bw_green = rgb("#8dc63f")
  let bw_gray = rgb("#808080")
  let table_head = rgb("#d5e8f0")
  let alert_bg = rgb("#fff8dc")

  // Calculate totals
  let remote_amount = remote_hours * remote_rate
  let onsite_amount = onsite_hours * onsite_rate
  let total = remote_amount + onsite_amount

  // Page setup
  set page(
    paper: "a4",
    margin: (top: 2.5cm, bottom: 3cm, left: 2cm, right: 2cm),
    footer: context {
      set text(size: 8pt, fill: bw_gray)
      grid(
        columns: (1fr, 1fr, 1fr),
        align: (left, center, right),
        [Raiba St. Florian/Schärding | BIC: RZOOAT2L522],
        [IBAN: AT46 2032 6000 0007 0623],
        link("https://www.blauweiss-edv.com")[www.blauweiss-edv.com]
      )
    }
  )

  // Font setup - modern Poppins
  set text(font: "Poppins", size: 10pt)
  show heading: set text(font: "Poppins", weight: "semibold")

  // Header with logo
  grid(
    columns: (1fr, 1fr),
    gutter: 1cm,
    // Logo
    if logo_path != none {
      image(logo_path, width: 5cm)
    } else {
      text(size: 24pt, weight: "bold", fill: bw_blue)[blau]
      text(size: 24pt, weight: "bold", fill: bw_green)[weiss]
    },
    // Company info
    align(right)[
      #text(weight: "bold")[BLAUWEISS-EDV LLC] \
      106 Stratford St \
      Houston, TX 77006 \
      USA \
      #v(0.3em)
      #text(fill: bw_blue)[+1 832 517 1100] \
      #link("mailto:info@blauweiss-edv.com")[#text(fill: bw_blue)[info\@blauweiss-edv.com]]
    ]
  )

  v(1.5cm)

  // Client address
  [
    #client_name \
    #client_address \
    #client_city \
    #if client_reg_id != "" [#v(0.2em) #client_reg_id] \
    #if client_vat_id != "" [USt-IdNr.: #client_vat_id]
  ]

  v(1cm)

  // Invoice details
  grid(
    columns: (1fr, 1fr),
    [#text(fill: bw_blue, weight: "bold")[Rechnung:] #invoice_number],
    [#text(weight: "bold")[Datum:] #text(fill: bw_blue)[#invoice_date]]
  )

  v(0.5cm)

  // Payment info box
  block(
    fill: alert_bg,
    stroke: bw_gray,
    inset: 10pt,
    width: 100%,
  )[
    #text(weight: "bold")[ACHTUNG!] Bitte berücksichtigen Sie die Bankverbindung: IBAN AT46 2032 6000 0007 0623 \
    #text(size: 9pt, fill: bw_gray)[Zahlungen treuhänderisch an M. Matejka bis Eröffnung US-Firmenkontos]
  ]

  v(1cm)

  [Sehr geehrte Damen und Herren!]

  v(0.5cm)

  [Bezugnehmend auf den Projektvertrag Nr. #text(weight: "bold")[#contract_number] erlauben wir uns unter Beilage des Leistungsscheines folgende Positionen in Rechnung zu stellen:]

  v(0.5cm)

  // VAT note box
  block(
    stroke: bw_gray,
    inset: 10pt,
    width: 100%,
  )[
    #text(weight: "bold")[Hinweis zur Umsatzsteuer:] Steuerschuldnerschaft des Leistungsempfängers \
    #text(size: 9pt)[(Reverse Charge gem. Art. 196 der Richtlinie 2006/112/EG – MwStSystRL)]
  ]

  v(0.5cm)

  // Invoice table
  table(
    columns: (1fr, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.5pt + bw_gray,
    fill: (_, y) => if y == 0 { table_head } else { none },
    inset: 8pt,
    
    [*Beschreibung*], [*Menge*], [*Einzelpreis*], [*Betrag*],
    [Beratungsleistung remote], [#remote_hours Ph], [à EUR #remote_rate], [EUR #remote_amount],
    [Beratungsleistung on-site], [#onsite_hours Ph], [à EUR #onsite_rate], [EUR #onsite_amount],
    table.cell(colspan: 3, align: right)[*Gesamt (netto)*], [*EUR #total*],
  )

  v(0.3cm)

  text(size: 9pt, fill: bw_gray)[
    Kein Ausweis von Umsatzsteuer – Leistungsempfänger schuldet die Steuer \
    #if client_vat_id != "" [Kunden-USt-IdNr.: #client_vat_id]
  ]

  v(0.5cm)

  [Wir bedanken uns für das Vertrauen, die gute Zusammenarbeit und sehen der Begleichung des Rechnungsbetrages unter den vereinbarten Zahlungsbedingungen an die genannte Bankverbindung entgegen.]

  v(0.3cm)

  [Für die gegenständliche Rechnung:]
  list[3% Skonto bei Sofortzahlung (1-2 Tage)]

  v(0.3cm)

  [Mit freundlichen Grüßen,]

  v(1.5cm)

  line(length: 6cm)
  [Autorisierte Unterschrift]

  v(0.5cm)

  text(weight: "bold")[Anlage:]
  list[Leistungsschein][Digitale Signatur]
}

// Generate invoice with example data
#invoice(
  invoice_number: "AR_001_2026",
  invoice_date: "03. Januar 2026",
  client_name: "nemensis AG Deutschland",
  client_address: "Alter Wall 69",
  client_city: "D - 20457 Hamburg",
  client_reg_id: "HRB. NR.: 181535 Hamburg",
  client_vat_id: "DE310161615",
  contract_number: "00003153",
  remote_hours: 184,
  remote_rate: 105,
  onsite_hours: 0,
  onsite_rate: 120,
)
