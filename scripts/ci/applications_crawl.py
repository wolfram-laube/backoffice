#!/usr/bin/env python3
"""
Applications Pipeline - Crawl Job
Crawls freelancermap.de for projects WITH DESCRIPTIONS
"""

import os
import sys
import json
import re
import time

sys.path.insert(0, os.getcwd())

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "de-DE,de;q=0.9",
}

def fetch_description(url, session):
    """Holt die Beschreibung von der Projekt-Detail-Seite."""
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            return ""
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Methode 1: div mit class*=description
        desc_div = soup.select_one("div[class*='description']")
        if desc_div:
            return desc_div.get_text(strip=True)[:2000]
        
        # Methode 2: H2 Beschreibung + nächstes Element
        for h2 in soup.select("h2"):
            if "beschreibung" in h2.get_text(strip=True).lower():
                next_elem = h2.find_next_sibling()
                if next_elem:
                    return next_elem.get_text(strip=True)[:2000]
        
        return ""
    except Exception as e:
        print(f"    ⚠️ Description fetch failed: {e}")
        return ""

def crawl_freelancermap(keyword, max_pages=2, fetch_details=True):
    """Crawlt freelancermap.de nach Projekten."""
    projects = []
    base_url = "https://www.freelancermap.de/projektboerse.html"
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for page in range(1, max_pages + 1):
        print(f"  📄 Seite {page}...")
        params = {"query": keyword, "sort": "1", "pagenr": page}
        
        try:
            resp = session.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            cards = soup.select("div.project-card")
            if not cards:
                break
            
            for card in cards:
                project = parse_card(card)
                if project:
                    projects.append(project)
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Error page {page}: {e}")
            break
    
    # Fetch descriptions für alle Projekte (mit Rate-Limiting)
    if fetch_details and projects:
        print(f"  📝 Fetching {len(projects)} descriptions...")
        for i, p in enumerate(projects):
            if i > 0 and i % 5 == 0:
                print(f"     ... {i}/{len(projects)}")
            p["description"] = fetch_description(p["url"], session)
            time.sleep(0.3)  # Rate limiting
    
    return projects

def parse_card(card):
    """Parst eine Projekt-Karte."""
    try:
        # Titel & URL
        title_elem = card.select_one("a[data-id='project-card-title'], a[href*='/projekt/']")
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        url = "https://www.freelancermap.de" + title_elem.get("href", "")
        
        # Company
        company_elem = card.select_one("div.project-info > div:first-child")
        company = company_elem.get_text(strip=True) if company_elem else ""
        
        # Location
        city_elem = card.select_one("[data-testid='city'] a, a[data-id='project-card-city']")
        location = city_elem.get_text(strip=True).rstrip(", ") if city_elem else ""
        
        # Remote %
        remote_elem = card.select_one("[data-testid='remoteInPercent']")
        remote_percent = 0
        if remote_elem:
            text = remote_elem.get_text()
            match = re.search(r"(\d+)\s*%", text)
            if match:
                remote_percent = int(match.group(1))
        
        # Duration
        duration_elem = card.select_one("[data-testid='duration']")
        duration = duration_elem.get_text(strip=True) if duration_elem else ""
        
        # Start
        start_elem = card.select_one("[data-testid='beginningMonth']")
        start_date = start_elem.get_text(strip=True) if start_elem else ""
        
        return {
            "title": title,
            "url": url,
            "company": company,
            "location": location,
            "remote_percent": remote_percent,
            "duration": duration,
            "start_date": start_date,
            "description": "",  # Wird später gefüllt
            "source": "freelancermap",
        }
        
    except Exception as e:
        print(f"    ⚠️ Parse error: {e}")
        return None

def main():
    keywords = os.environ.get("KEYWORDS", "DevOps,Python,AI").split(",")
    min_remote = int(os.environ.get("MIN_REMOTE", "75"))
    max_pages = int(os.environ.get("MAX_PAGES", "2"))
    fetch_details = os.environ.get("FETCH_DETAILS", "true").lower() == "true"
    
    all_projects = []
    
    for kw in keywords:
        kw = kw.strip()
        print(f"🔍 Searching: {kw}")
        
        projects = crawl_freelancermap(kw, max_pages=max_pages, fetch_details=fetch_details)
        print(f"   → {len(projects)} raw results")
        
        # Filter by remote
        if min_remote > 0:
            projects = [p for p in projects if p.get("remote_percent", 0) >= min_remote]
            print(f"   → {len(projects)} after remote filter (>={min_remote}%)")
        
        all_projects.extend(projects)
    
    # Deduplicate
    seen = set()
    unique = []
    for p in all_projects:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)
    
    os.makedirs("output", exist_ok=True)
    with open("output/projects.json", "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {len(unique)} unique projects saved to output/projects.json")
    
    # Show sample with description
    with_desc = sum(1 for p in unique if p.get("description"))
    print(f"📝 {with_desc}/{len(unique)} have descriptions")
    
    for p in unique[:3]:
        print(f"  • {p['title'][:45]}...")
        if p.get('description'):
            print(f"    Desc: {p['description'][:80]}...")

if __name__ == "__main__":
    main()
