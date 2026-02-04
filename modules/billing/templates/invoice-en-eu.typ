// BLAUWEISS Invoice Template - EU (English, EUR, Reverse Charge)
// Usage: typst compile invoice-en-eu.typ

#let invoice(
  invoice_number: "AR_001_2026",
  invoice_date: "January 03, 2026",
  client_name: "Example Company B.V.",
  client_address: "Keizersgracht 123",
  client_city: "1015 CW Amsterdam",
  client_country: "The Netherlands",
  client_reg_id: "KVK: 12345678",
  client_vat_id: "NL123456789B01",
  contract_number: "00003152",
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
    #client_country \
    #if client_reg_id != "" [#v(0.2em) #client_reg_id] \
    #if client_vat_id != "" [VAT ID: #client_vat_id]
  ]

  v(1cm)

  // Invoice details
  grid(
    columns: (1fr, 1fr),
    [#text(fill: bw_blue, weight: "bold")[Invoice:] #invoice_number],
    [#text(weight: "bold")[Date:] #text(fill: bw_blue)[#invoice_date]]
  )

  v(0.5cm)

  // Payment info box
  block(
    fill: alert_bg,
    stroke: bw_gray,
    inset: 10pt,
    width: 100%,
  )[
    #text(weight: "bold")[ATTENTION!] Please note the bank details: IBAN AT46 2032 6000 0007 0623 \
    #text(size: 9pt, fill: bw_gray)[Payments held in trust by M. Matejka until US company account is opened]
  ]

  v(1cm)

  [Dear Sir or Madam,]

  v(0.5cm)

  [With reference to project contract no. #text(weight: "bold")[#contract_number], we hereby invoice the following services, enclosed with the service report:]

  v(0.5cm)

  // VAT note box
  block(
    stroke: bw_gray,
    inset: 10pt,
    width: 100%,
  )[
    #text(weight: "bold")[VAT Note:] VAT reverse charge – customer to account for VAT \
    #text(size: 9pt)[(per Article 196 of Directive 2006/112/EC)]
  ]

  v(0.5cm)

  // Invoice table
  table(
    columns: (1fr, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.5pt + bw_gray,
    fill: (_, y) => if y == 0 { table_head } else { none },
    inset: 8pt,
    
    [*Description*], [*Quantity*], [*Unit Price*], [*Amount*],
    [Remote consulting services], [#remote_hours hrs], [EUR #remote_rate], [EUR #remote_amount],
    [On-site consulting services], [#onsite_hours hrs], [EUR #onsite_rate], [EUR #onsite_amount],
    table.cell(colspan: 3, align: right)[*Total (net)*], [*EUR #total*],
  )

  v(0.3cm)

  text(size: 9pt, fill: bw_gray)[
    No VAT charged – reverse charge applies, customer is liable for VAT \
    #if client_vat_id != "" [Customer VAT ID: #client_vat_id]
  ]

  v(0.5cm)

  [We thank you for your trust and the good cooperation. Please remit the invoice amount to the bank account stated above according to the agreed payment terms.]

  v(0.3cm)

  [For this invoice:]
  list[3% discount for immediate payment (1-2 days)]

  v(0.3cm)

  [Kind regards,]

  v(1.5cm)

  line(length: 6cm)
  [Authorized Signature]

  v(0.5cm)

  text(weight: "bold")[Enclosure:]
  list[Service Report][Digital Signature]
}

// Generate invoice with example data
#invoice(
  invoice_number: "AR_003_2026",
  invoice_date: "January 03, 2026",
  client_name: "Example Company B.V.",
  client_address: "Keizersgracht 123",
  client_city: "1015 CW Amsterdam",
  client_country: "The Netherlands",
  client_reg_id: "KVK: 12345678",
  client_vat_id: "NL123456789B01",
  contract_number: "00003152",
  remote_hours: 184,
  remote_rate: 105,
  onsite_hours: 0,
  onsite_rate: 120,
)
