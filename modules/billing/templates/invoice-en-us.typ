// BLAUWEISS Invoice Template - US (English, USD)
// Usage: typst compile invoice-en-us.typ

#let invoice(
  invoice_number: "AR_001_2026",
  invoice_date: "January 03, 2026",
  client_name: "Example Corp.",
  client_address: "123 Main Street, Suite 400",
  client_city: "Austin, TX 78701",
  client_country: "USA",
  contract_number: "00003151",
  payment_terms: "Net 30",
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
      #link("mailto:info@blauweiss-edv.com")[#text(fill: bw_blue)[info\@blauweiss-edv.com]] \
      #v(0.3em)
      EIN: XX-XXXXXXX
    ]
  )

  v(1.5cm)

  // Bill To
  text(weight: "bold")[Bill To:]
  v(0.3em)
  [
    #client_name \
    #client_address \
    #client_city \
    #client_country
  ]

  v(1cm)

  // Invoice details
  grid(
    columns: (1fr, 1fr, 1fr),
    [#text(fill: bw_blue, weight: "bold")[Invoice:] #invoice_number],
    [#text(weight: "bold")[Date:] #text(fill: bw_blue)[#invoice_date]],
    [#text(weight: "bold")[Terms:] #payment_terms]
  )

  v(0.5cm)

  // Payment info box
  block(
    fill: alert_bg,
    stroke: bw_gray,
    inset: 10pt,
    width: 100%,
  )[
    #text(weight: "bold")[Payment Information:] Please remit to IBAN AT46 2032 6000 0007 0623 (BIC: RZOOAT2L522) \
    #text(size: 9pt, fill: bw_gray)[Payments held in trust by M. Matejka until US company account is opened]
  ]

  v(1cm)

  [Dear Sir or Madam,]

  v(0.5cm)

  [With reference to project contract no. #text(weight: "bold")[#contract_number], please find below our invoice for services rendered:]

  v(0.5cm)

  // Invoice table
  table(
    columns: (1fr, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.5pt + bw_gray,
    fill: (_, y) => if y == 0 { table_head } else { none },
    inset: 8pt,
    
    [*Description*], [*Quantity*], [*Unit Price*], [*Amount*],
    [Remote consulting services], [#remote_hours hrs], [USD #remote_rate], [USD #remote_amount],
    [On-site consulting services], [#onsite_hours hrs], [USD #onsite_rate], [USD #onsite_amount],
    table.cell(colspan: 3, align: right)[*Total Due*], [*USD #total*],
  )

  v(0.5cm)

  [Payment is due within 30 days of invoice date.]
  list[3% discount for payment within 5 days]

  v(0.5cm)

  [Thank you for your business!]

  v(1.5cm)

  line(length: 6cm)
  [Authorized Signature]

  v(0.5cm)

  text(weight: "bold")[Enclosure:]
  list[Service Report]
}

// Generate invoice with example data
#invoice(
  invoice_number: "AR_002_2026",
  invoice_date: "January 03, 2026",
  client_name: "Occidental Petroleum Corporation",
  client_address: "5 Greenway Plaza, Suite 110",
  client_city: "Houston, TX 77046",
  client_country: "USA",
  contract_number: "00003151",
  remote_hours: 184,
  remote_rate: 105,
  onsite_hours: 0,
  onsite_rate: 120,
)
