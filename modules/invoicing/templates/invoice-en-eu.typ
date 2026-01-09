// =============================================================================
// BLAUWEISS-EDV LLC – Invoice Template (English, EU Customers)
// =============================================================================
// Usage: Adjust variables at top, then `typst compile invoice.typ`
// VAT Reverse Charge per Article 196 of Directive 2006/112/EC
// =============================================================================

// === INVOICE DATA (adjust here) ===
#let invoice_nr = "OP_AR001_2025"
#let invoice_date = "December 19, 2025"
#let project_nr = "00003151"

// Customer
#let customer_name = "Example Company B.V."
#let customer_address = "Keizersgracht 123"
#let customer_city = "1015 CW Amsterdam"
#let customer_country = "The Netherlands"
#let customer_reg_nr = "KVK: 12345678"
#let customer_vat_id = "NL123456789B01"  // Customer VAT-ID (required for reverse charge)

// Line items: (Description, Quantity, Unit, Unit Price)
#let line_items = (
  ("Remote consulting services", 184.00, "hrs", 105.00),
  ("On-site consulting services", 0.00, "hrs", 120.00),
)

// Payment terms
#let discount_text = "3% discount for immediate payment (1-2 days)"

// === COMPANY DATA (usually fixed) ===
#let company_name = "BLAUWEISS-EDV LLC"
#let company_address = "106 Stratford St"
#let company_city = "Houston, TX 77006"
#let company_country = "USA"
#let company_phone = "+1 832 517 1100"
#let company_email = "info@blauweiss-edv.com"
#let company_web = "www.blauweiss-edv.com"
#let company_ein = "XX-XXXXXXX"  // LLC's EIN (to be obtained)

// Bank details (fiduciary until US account opened)
#let bank_name = "Raiba St. Florian/Schärding"
#let bank_iban = "AT46 2032 6000 0007 0623"
#let bank_bic = "RZOOAT2L522"
#let bank_note = "Payments held in trust by M. Matejka until US company account is opened"

// === COLORS ===
#let blue = rgb("#1e5a99")
#let green = rgb("#8dc63f")
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

#set text(font: "Space Grotesk", size: 10pt)

// === HEADER WITH LOGO ===
#grid(
  columns: (1fr, auto),
  gutter: 1cm,
  [
    // Logo
    #text(size: 24pt, fill: rgb("#1e5a99"), weight: "bold")[BLAUWEISS-EDV LLC]
  ],
  [
    // Company address on right
    #box(
      fill: light_cyan,
      inset: 10pt,
      radius: 3pt,
    )[
      #set text(size: 9pt)
      #strong[#company_name]
      
      #company_address \
      #company_city \
      #company_country
      
      #v(0.3cm)
      #text(fill: cyan)[#company_phone] \
      #text(fill: cyan)[#company_email]
    ]
  ]
)

#v(1cm)

// === CUSTOMER ADDRESS ===
#customer_name \
#customer_address \
#customer_city \
#customer_country \
#customer_reg_nr \
VAT ID: #customer_vat_id

#v(1cm)

// === INVOICE TITLE ===
#grid(
  columns: (auto, auto),
  gutter: 2cm,
  [#strong[Invoice:] #text(fill: cyan)[#invoice_nr]],
  [#strong[Date:] #text(fill: cyan)[#invoice_date]],
)

#v(0.5cm)

// === BANK DETAILS NOTICE ===
#box(
  width: 100%,
  fill: rgb("#fff3cd"),
  inset: 8pt,
  radius: 3pt,
)[
  #text(size: 9pt)[
    *ATTENTION!* Please note the bank details: IBAN #bank_iban \
    #text(size: 8pt, fill: gray)[#bank_note]
  ]
]

#v(0.5cm)

// === LETTER TEXT ===
Dear Sir or Madam,

With reference to project contract no. #strong[#project_nr], we hereby invoice the following services, enclosed with the service report:

#v(0.3cm)

#box(
  width: 100%,
  fill: rgb("#f0f0f0"),
  inset: 8pt,
  radius: 3pt,
)[
  #text(size: 9pt)[
    *VAT Note:* VAT reverse charge – customer to account for VAT \
    (per Article 196 of Directive 2006/112/EC)
  ]
]

#v(0.5cm)

// === LINE ITEMS TABLE ===
#let total = line_items.map(p => p.at(1) * p.at(3)).sum()

#table(
  columns: (2fr, 1fr, 1fr, 1fr),
  align: (left, right, right, right),
  stroke: 0.5pt + gray,
  inset: 8pt,
  
  // Header
  table.header(
    [*Description*], [*Quantity*], [*Unit Price*], [*Amount*],
  ),
  
  // Line items
  ..line_items.map(p => {
    let amount = p.at(1) * p.at(3)
    (
      p.at(0),
      [#p.at(1) #p.at(2)],
      [EUR #str(p.at(3))],
      [EUR #str(calc.round(amount, digits: 2))],
    )
  }).flatten(),
  
  // Total
  table.cell(colspan: 3, align: right)[*Total (net)*],
  [*EUR #str(calc.round(total, digits: 2))*],
)

#v(0.3cm)

#text(size: 9pt, fill: gray)[
  No VAT charged – reverse charge applies, customer is liable for VAT \
  Customer VAT ID: #customer_vat_id
]

#v(0.5cm)

// === PAYMENT TERMS ===
We thank you for your trust and the good cooperation. Please remit the invoice amount to the bank account stated above according to the agreed payment terms.

For this invoice:
- #discount_text

#v(1cm)

Kind regards,

#v(1.5cm)

// Signature area
#line(length: 5cm, stroke: 0.5pt + gray)
#text(size: 8pt, fill: gray)[Authorized Signature]

#v(0.5cm)

*Enclosure:*
- Service Report
- Digital Signature
