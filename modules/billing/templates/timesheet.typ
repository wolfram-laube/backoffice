// BLAUWEISS Timesheet / Leistungsschein
// Automatically handles month lengths, weekends, and holidays (DE/AT)
// Multi-language support: EN, DE, VI, AR, IS

#let timesheet(
  year: 2026,
  month: 1,
  client_name: "Example Client",
  client_short: "EX",
  project_name: "Consulting Services",
  contract_number: "00003151",
  consultant_name: "Max Mustermann",
  country: "AT",  // "DE" or "AT" for holiday calculation
  lang: "de",     // "en", "de", "vi", "ar", "is"
  // Daily hours as dictionary: day -> (hours, description)
  daily_entries: (:),
  logo_path: "logo.jpg",
  approver_name: "",      // Name of person approving the timesheet
  approver_title: "",     // Title/role of approver
) = {
  // Colors
  let bw_blue = rgb("#00aeef")
  let bw_green = rgb("#8dc63f")
  let bw_gray = rgb("#808080")
  let bw_light_gray = rgb("#e8e8e8")
  let weekend_color = rgb("#ff6b6b")      // Bold red
  let holiday_color = rgb("#ffd93d")       // Bold yellow
  let header_color = rgb("#00aeef")        // BlauWeiss blue
  let header_text = white

  // ============================================
  // TRANSLATIONS
  // ============================================
  let t = (
    // Title
    title: (
      en: "Timesheet / Service Report",
      de: "Leistungsschein / Timesheet",
      vi: "Bảng Chấm Công",
      ar: "كشف الحضور",
      is: "Tímaskýrsla",
    ),
    // Headers
    project: (
      en: "Project:",
      de: "Projekt:",
      vi: "Dự án:",
      ar: "المشروع:",
      is: "Verkefni:",
    ),
    contract: (
      en: "Contract:",
      de: "Vertrag:",
      vi: "Hợp đồng:",
      ar: "العقد:",
      is: "Samningur:",
    ),
    country_label: (
      en: "Country:",
      de: "Land:",
      vi: "Quốc gia:",
      ar: "البلد:",
      is: "Land:",
    ),
    client: (
      en: "Client",
      de: "Auftraggeber / Client",
      vi: "Khách hàng",
      ar: "العميل",
      is: "Viðskiptavinur",
    ),
    consultant: (
      en: "Consultant",
      de: "Berater / Consultant",
      vi: "Tư vấn viên",
      ar: "المستشار",
      is: "Ráðgjafi",
    ),
    // Table headers
    day: (
      en: "Day",
      de: "Tag",
      vi: "Thứ",
      ar: "اليوم",
      is: "Dagur",
    ),
    date: (
      en: "Date",
      de: "Datum",
      vi: "Ngày",
      ar: "التاريخ",
      is: "Dagsetning",
    ),
    hours: (
      en: "Hrs",
      de: "Std",
      vi: "Giờ",
      ar: "ساعات",
      is: "Klst",
    ),
    description: (
      en: "Description",
      de: "Beschreibung / Description",
      vi: "Mô tả",
      ar: "الوصف",
      is: "Lýsing",
    ),
    notes: (
      en: "Notes",
      de: "Notizen",
      vi: "Ghi chú",
      ar: "ملاحظات",
      is: "Athugasemdir",
    ),
    total: (
      en: "Total",
      de: "Gesamt / Total",
      vi: "Tổng cộng",
      ar: "المجموع",
      is: "Samtals",
    ),
    hours_label: (
      en: "Hours",
      de: "Stunden / Hours",
      vi: "Giờ làm việc",
      ar: "ساعات العمل",
      is: "Klukkustundir",
    ),
    // Legend
    weekend: (
      en: "Weekend",
      de: "Wochenende",
      vi: "Cuối tuần",
      ar: "عطلة نهاية الأسبوع",
      is: "Helgi",
    ),
    holiday: (
      en: "Holiday",
      de: "Feiertag",
      vi: "Ngày lễ",
      ar: "عطلة رسمية",
      is: "Frídagur",
    ),
    both: (
      en: "both",
      de: "beide",
      vi: "cả hai",
      ar: "كلاهما",
      is: "bæði",
    ),
    // Signatures
    sig_date: (
      en: "Date",
      de: "Datum",
      vi: "Ngày",
      ar: "التاريخ",
      is: "Dagsetning",
    ),
    sig_consultant: (
      en: "Consultant Signature",
      de: "Unterschrift Berater",
      vi: "Chữ ký Tư vấn viên",
      ar: "توقيع المستشار",
      is: "Undirskrift ráðgjafa",
    ),
    sig_client: (
      en: "Client Signature",
      de: "Unterschrift Auftraggeber",
      vi: "Chữ ký Khách hàng",
      ar: "توقيع العميل",
      is: "Undirskrift viðskiptavinar",
    ),
    // Countries
    austria: (
      en: "Austria",
      de: "Österreich",
      vi: "Áo",
      ar: "النمسا",
      is: "Austurríki",
    ),
    germany: (
      en: "Germany",
      de: "Deutschland",
      vi: "Đức",
      ar: "ألمانيا",
      is: "Þýskaland",
    ),
  )

  // Helper to get translation
  let tr(key) = {
    t.at(key).at(lang, default: t.at(key).at("en"))
  }

  // Month names per language
  let month_names = (
    en: ("January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"),
    de: ("Januar", "Februar", "März", "April", "Mai", "Juni",
         "Juli", "August", "September", "Oktober", "November", "Dezember"),
    vi: ("Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
         "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"),
    ar: ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
         "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"),
    is: ("janúar", "febrúar", "mars", "apríl", "maí", "júní",
         "júlí", "ágúst", "september", "október", "nóvember", "desember"),
  )
  
  // Day names (short) per language
  let day_names = (
    en: ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    de: ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
    vi: ("T2", "T3", "T4", "T5", "T6", "T7", "CN"),
    ar: ("ن", "ث", "ر", "خ", "ج", "س", "ح"),
    is: ("Mán", "Þri", "Mið", "Fim", "Fös", "Lau", "Sun"),
  )

  let get_month_name() = {
    month_names.at(lang, default: month_names.en).at(month - 1)
  }

  let get_day_name(dow) = {
    day_names.at(lang, default: day_names.en).at(dow)
  }

  // Days in month calculation
  let days_in_month = if month in (1, 3, 5, 7, 8, 10, 12) { 31 }
    else if month in (4, 6, 9, 11) { 30 }
    else if calc.rem(year, 4) == 0 and (calc.rem(year, 100) != 0 or calc.rem(year, 400) == 0) { 29 }
    else { 28 }

  // Day of week calculation (Zeller's congruence simplified)
  let day_of_week(y, m, d) = {
    let yy = if m < 3 { y - 1 } else { y }
    let mm = if m < 3 { m + 12 } else { m }
    let q = d
    let k = calc.rem(yy, 100)
    let j = calc.floor(yy / 100)
    let h = calc.rem(q + calc.floor((13 * (mm + 1)) / 5) + k + calc.floor(k / 4) + calc.floor(j / 4) - 2 * j, 7)
    let dow = calc.rem(h + 5, 7)
    dow
  }

  // Easter calculation (Anonymous Gregorian algorithm)
  let easter_day(y) = {
    let a = calc.rem(y, 19)
    let b = calc.floor(y / 100)
    let c = calc.rem(y, 100)
    let d = calc.floor(b / 4)
    let e = calc.rem(b, 4)
    let f = calc.floor((b + 8) / 25)
    let g = calc.floor((b - f + 1) / 3)
    let h = calc.rem(19 * a + b - d - g + 15, 30)
    let i = calc.floor(c / 4)
    let k = calc.rem(c, 4)
    let l = calc.rem(32 + 2 * e + 2 * i - h - k, 7)
    let m = calc.floor((a + 11 * h + 22 * l) / 451)
    let month = calc.floor((h + l - 7 * m + 114) / 31)
    let day = calc.rem(h + l - 7 * m + 114, 31) + 1
    (month, day)
  }

  // Get holidays for country
  let get_holidays(y, m, ctry) = {
    let holidays = (:)
    let easter = easter_day(y)
    let easter_month = easter.at(0)
    let easter_day_num = easter.at(1)
    
    let easter_plus(days) = {
      let d = easter_day_num + days
      let em = easter_month
      let days_in_easter_month = if em == 3 { 31 } else { 30 }
      if d > days_in_easter_month {
        (em + 1, d - days_in_easter_month)
      } else if d < 1 {
        (em - 1, if em == 4 { 31 + d } else { 30 + d })
      } else {
        (em, d)
      }
    }

    // Fixed holidays
    if m == 1 {
      holidays.insert("1", "Neujahr 🇦🇹🇩🇪")
      if ctry == "AT" { holidays.insert("6", "Hl. Drei Könige 🇦🇹") }
    }
    if m == 5 {
      holidays.insert("1", "Tag der Arbeit 🇦🇹🇩🇪")
    }
    if m == 10 {
      if ctry == "DE" { holidays.insert("3", "Tag der Einheit 🇩🇪") }
      if ctry == "AT" { holidays.insert("26", "Nationalfeiertag 🇦🇹") }
    }
    if m == 11 {
      if ctry == "AT" { holidays.insert("1", "Allerheiligen 🇦🇹") }
    }
    if m == 12 {
      if ctry == "AT" { holidays.insert("8", "Mariä Empfängnis 🇦🇹") }
      holidays.insert("25", "Weihnachten 🇦🇹🇩🇪")
      holidays.insert("26", "Stefanitag 🇦🇹🇩🇪")
    }
    if m == 8 {
      if ctry == "AT" { holidays.insert("15", "Mariä Himmelfahrt 🇦🇹") }
    }

    // Easter-based holidays
    let kf = easter_plus(-2)
    if kf.at(0) == m and ctry == "DE" {
      holidays.insert(str(kf.at(1)), "Karfreitag 🇩🇪")
    }
    
    let om = easter_plus(1)
    if om.at(0) == m {
      holidays.insert(str(om.at(1)), "Ostermontag 🇦🇹🇩🇪")
    }
    
    let ch = easter_plus(39)
    if ch.at(0) == m {
      holidays.insert(str(ch.at(1)), "Chr. Himmelfahrt 🇦🇹🇩🇪")
    }
    
    let pm = easter_plus(50)
    if pm.at(0) == m {
      holidays.insert(str(pm.at(1)), "Pfingstmontag 🇦🇹🇩🇪")
    }
    
    let fl = easter_plus(60)
    if fl.at(0) == m {
      holidays.insert(str(fl.at(1)), "Fronleichnam 🇦🇹🇩🇪")
    }

    holidays
  }

  let holidays = get_holidays(year, month, country)

  // Calculate totals
  let total_hours = daily_entries.values().map(e => e.at(0)).sum(default: 0)

  // Page setup - Landscape
  set page(
    paper: "a4",
    flipped: true,
    margin: (top: 2cm, bottom: 2cm, left: 1.5cm, right: 1.5cm),
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

  // Font
  set text(font: "Poppins", size: 9pt)

  // Header
  grid(
    columns: (1fr, 2fr, 1fr),
    gutter: 1cm,
    if logo_path != none {
      image(logo_path, width: 4cm)
    },
    align(center)[
      #text(size: 18pt, weight: "bold", fill: bw_blue)[#tr("title")] \
      #v(0.3em)
      #text(size: 14pt)[#get_month_name() #year]
    ],
    align(right)[
      #text(size: 8pt)[
        #text(weight: "bold")[#tr("project")] #project_name \
        #text(weight: "bold")[#tr("contract")] #contract_number \
        #text(weight: "bold")[#tr("country_label")] #if country == "AT" [🇦🇹 #tr("austria")] else [🇩🇪 #tr("germany")]
      ]
    ]
  )

  v(0.5cm)

  // Client and Consultant info
  grid(
    columns: (1fr, 1fr),
    gutter: 2cm,
    [
      #text(weight: "bold", fill: bw_gray)[#tr("client")] \
      #client_name
    ],
    [
      #text(weight: "bold", fill: bw_gray)[#tr("consultant")] \
      #consultant_name
    ]
  )

  v(0.5cm)

  // Legend
  box(
    fill: bw_light_gray,
    inset: 8pt,
    radius: 4pt,
    width: 100%,
  )[
    #text(size: 8pt, weight: "medium")[
      #box(fill: weekend_color, inset: 4pt, radius: 2pt)[#text(fill: white)[Sa/So]] #tr("weekend")
      #h(1cm)
      #box(fill: holiday_color, inset: 4pt, radius: 2pt)[#text(weight: "bold")[F]] #tr("holiday")
      #h(1cm)
      🇦🇹 = AT
      #h(0.5cm)
      🇩🇪 = DE
      #h(0.5cm)
      🇦🇹🇩🇪 = #tr("both")
    ]
  ]

  v(0.5cm)

  // Calendar table
  let header_cells = (
    text(fill: header_text, weight: "bold")[#tr("day")],
    text(fill: header_text, weight: "bold")[#tr("date")],
    text(fill: header_text, weight: "bold")[#tr("hours")],
    text(fill: header_text, weight: "bold")[#tr("description")],
    text(fill: header_text, weight: "bold")[#tr("notes")],
  )

  let rows = ()
  
  for day in range(1, days_in_month + 1) {
    let dow = day_of_week(year, month, day)
    let is_weekend = dow >= 5
    let day_str = str(day)
    let is_holiday = day_str in holidays
    
    let bg_color = if is_holiday { holiday_color } 
      else if is_weekend { weekend_color } 
      else { none }
    
    let text_color = if is_weekend and not is_holiday { white } else { black }
    
    let day_name = get_day_name(dow)
    let date_str = [#day.#month.#year]
    
    let entry = daily_entries.at(day_str, default: (0, ""))
    let hours = entry.at(0)
    let desc = entry.at(1)
    
    let holiday_name = if is_holiday { holidays.at(day_str) } else { "" }
    let notes = if is_holiday { holiday_name } else { "" }
    
    rows.push((
      table.cell(fill: bg_color)[#text(fill: text_color)[#day_name]],
      table.cell(fill: bg_color)[#text(fill: text_color)[#date_str]],
      table.cell(fill: bg_color)[#text(fill: text_color)[#if hours > 0 [#hours] else if is_weekend or is_holiday [—] else []]],
      table.cell(fill: bg_color)[#text(fill: text_color)[#desc]],
      table.cell(fill: bg_color)[#text(fill: text_color)[#notes]],
    ))
  }

  table(
    columns: (auto, auto, auto, 1fr, 1fr),
    align: (center, center, center, left, left),
    stroke: 0.5pt + bw_gray,
    inset: 6pt,
    fill: (_, y) => if y == 0 { header_color } else { none },
    
    ..header_cells,
    ..rows.flatten(),
    
    // Total row
    table.cell(colspan: 2, fill: header_color)[#text(fill: header_text, weight: "bold")[#tr("total")]],
    table.cell(fill: header_color)[#text(fill: header_text, weight: "bold")[#total_hours]],
    table.cell(colspan: 2, fill: header_color)[#text(fill: header_text)[#tr("hours_label")]],
  )

  v(1cm)

  // Signature section
  grid(
    columns: (1fr, 1fr),
    gutter: 2cm,
    [
      #text(size: 9pt, weight: "bold")[#consultant_name]
      #v(0.1cm)
      #text(size: 8pt, fill: bw_gray)[BlauWeiss EDV LLC]
      #v(0.8cm)
      #line(length: 6cm)
      #v(0.2cm)
      #text(size: 8pt)[#tr("sig_date"), #tr("sig_consultant")]
    ],
    [
      #if approver_name != "" [
        #text(size: 9pt, weight: "bold")[#approver_name]
        #v(0.1cm)
        #text(size: 8pt, fill: bw_gray)[#if approver_title != "" [#approver_title, ] #client_name]
      ] else [
        #v(1.1cm)
      ]
      #v(0.8cm)
      #line(length: 6cm)
      #v(0.2cm)
      #text(size: 8pt)[#tr("sig_date"), #tr("sig_client")]
    ]
  )
}

// Example: January 2026 timesheet (German)
#timesheet(
  year: 2026,
  month: 1,
  client_name: "nemensis AG Deutschland",
  client_short: "NEM",
  project_name: "CLARISSA Development",
  contract_number: "00003153",
  consultant_name: "Wolfram Laube",
  country: "AT",
  lang: "de",
  approver_name: "Max Mustermann",
  approver_title: "Projektleiter",
  daily_entries: (
    "2": (8, "Architecture review"),
    "5": (6, "API development"),
    "6": (8, "API development"),
    "7": (8, "Testing"),
    "8": (4, "Documentation"),
    "9": (8, "Sprint planning"),
    "12": (8, "Feature implementation"),
    "13": (8, "Feature implementation"),
    "14": (6, "Code review"),
    "15": (8, "Bug fixes"),
    "16": (8, "Integration testing"),
    "19": (8, "Performance optimization"),
    "20": (8, "Database migration"),
    "21": (8, "Deployment preparation"),
    "22": (4, "Team meeting"),
    "23": (8, "Production deployment"),
    "26": (8, "Monitoring setup"),
    "27": (8, "Documentation"),
    "28": (8, "Knowledge transfer"),
    "29": (6, "Sprint retrospective"),
    "30": (8, "Planning Q2"),
  ),
)
