#!/usr/bin/env python3
"""
Applications Pipeline - Match Job
Matches projects (with descriptions!) against all profile combinations
Now with better sorting: AI/KI projects prioritized!
"""

import os
import sys
import json
from collections import defaultdict

sys.path.insert(0, os.getcwd())

from src.admin.applications.pipeline.profiles import PROFILES, TEAM_COMBOS, WOLFRAM, IAN, MICHAEL

# AI/KI Keywords für Priorisierung
AI_KEYWORDS = {"ki", "ai", "llm", "ml", "genai", "machine learning", "deep learning", 
               "rag", "nlp", "gpt", "neural", "tensorflow", "pytorch", "data scientist"}

def is_ai_project(project):
    """Prüft ob ein Projekt ein echtes AI/KI Projekt ist (im Titel!)."""
    title = project.get("title", "").lower()
    return any(kw in title for kw in AI_KEYWORDS)

def match_solo(project, profile):
    """Match gegen ein Solo-Profil mit Titel + Beschreibung."""
    search_text = " ".join([
        project.get("title", ""),
        project.get("description", ""),
        " ".join(project.get("skills", [])),
    ]).lower()
    
    return profile.match_score(search_text)

def match_team(project, team_config):
    """Match gegen ein Team-Combo mit Titel + Beschreibung."""
    search_text = " ".join([
        project.get("title", ""),
        project.get("description", ""),
        " ".join(project.get("skills", [])),
    ]).lower()
    
    keywords = team_config.get("keywords", set())
    matches = []
    for kw in keywords:
        if kw.lower() in search_text:
            matches.append(kw)
    
    if len(matches) >= 6:
        score = min(100, 70 + (len(matches) - 6) * 5)
    elif len(matches) >= 3:
        score = 50 + (len(matches) - 3) * 7
    elif len(matches) >= 1:
        score = 20 + (len(matches) - 1) * 15
    else:
        score = 0
    
    return {
        "percentage": score,
        "matches": {"keywords": matches},
        "excluded_by": None
    }

def sort_matches(matches):
    """Sortiert Matches: AI-Projekte zuerst, dann nach Score."""
    def sort_key(m):
        is_ai = is_ai_project(m["project"])
        # AI-Projekte bekommen Bonus von 1000 für Sortierung
        return (-(1000 if is_ai else 0) - m["score"], m["project"]["title"])
    return sorted(matches, key=sort_key)

def main():
    min_score = int(os.environ.get("MIN_SCORE", "30"))
    
    with open("output/projects.json") as f:
        projects = json.load(f)
    
    with_desc = sum(1 for p in projects if p.get("description"))
    ai_count = sum(1 for p in projects if is_ai_project(p))
    
    print(f"📊 Matching {len(projects)} projects ({with_desc} with desc, {ai_count} AI/KI)")
    print(f"   Min score: {min_score}%")
    print("=" * 70)
    
    results = defaultdict(list)
    
    # SOLO MATCHES
    solo_profiles = {"wolfram": WOLFRAM, "ian": IAN, "michael": MICHAEL}
    
    for project in projects:
        for name, profile in solo_profiles.items():
            result = match_solo(project, profile)
            if result["percentage"] >= min_score and not result.get("excluded_by"):
                results[name].append({
                    "project": project,
                    "score": result["percentage"],
                    "keywords": result["matches"].get("must_have", [])[:5],
                    "is_ai": is_ai_project(project),
                })
    
    # TEAM MATCHES
    for team_name, team_config in TEAM_COMBOS.items():
        for project in projects:
            result = match_team(project, team_config)
            if result["percentage"] >= min_score:
                results[team_name].append({
                    "project": project,
                    "score": result["percentage"],
                    "keywords": result["matches"].get("keywords", [])[:8],
                    "is_ai": is_ai_project(project),
                })
    
    # OUTPUT
    print()
    print("🧑 SOLO MATCHES")
    print("-" * 70)
    
    for name in ["wolfram", "ian", "michael"]:
        matches = sort_matches(results[name])
        hot = sum(1 for m in matches if m["score"] >= 70)
        good = sum(1 for m in matches if 50 <= m["score"] < 70)
        ai_matches = sum(1 for m in matches if m["is_ai"])
        print(f"\n{name.upper()} ({len(matches)} matches, 🔥{hot} HOT, 🤖{ai_matches} AI):")
        for m in matches[:10]:
            p = m["project"]
            icon = "🤖" if m["is_ai"] else ("🔥" if m["score"] >= 70 else "✅")
            print(f"  {icon}[{m['score']:3d}%] {p['title'][:42]}... ({p['remote_percent']}%R)")
            if m.get("keywords"):
                print(f"          → {', '.join(m['keywords'][:5])}")
    
    print()
    print("👥 TEAM MATCHES") 
    print("-" * 70)
    
    team_order = ["wolfram_ian", "wolfram_michael", "ian_michael", "all_three"]
    for team_name in team_order:
        if team_name in results and results[team_name]:
            matches = sort_matches(results[team_name])
            display = TEAM_COMBOS[team_name]["name"]
            hot = sum(1 for m in matches if m["score"] >= 70)
            ai_matches = sum(1 for m in matches if m["is_ai"])
            print(f"\n{display} ({len(matches)} matches, 🔥{hot} HOT, 🤖{ai_matches} AI):")
            for m in matches[:7]:
                p = m["project"]
                icon = "🤖" if m["is_ai"] else ("🔥" if m["score"] >= 70 else "✅")
                print(f"  {icon}[{m['score']:3d}%] {p['title'][:42]}... ({p['remote_percent']}%R)")
                if m.get("keywords"):
                    print(f"          → {', '.join(m['keywords'][:6])}")
    
    # SUMMARY
    print()
    print("=" * 70)
    print("📊 ZUSAMMENFASSUNG")
    print("-" * 70)
    
    total_hot = 0
    all_names = ["wolfram", "ian", "michael"] + team_order
    
    for name in all_names:
        if name in results:
            matches = results[name]
            hot = sum(1 for m in matches if m["score"] >= 70)
            ai_m = sum(1 for m in matches if m["is_ai"])
            total_hot += hot
            display = TEAM_COMBOS.get(name, {}).get("name", name.upper())[:30]
            print(f"  {display:32s}: {len(matches):3d} | 🔥 {hot:2d} HOT | 🤖 {ai_m:2d} AI")
    
    print()
    print(f"🔥 {total_hot} HOT matches (>=70%) insgesamt!")
    
    # Save JSON - ALLE Matches speichern, nicht nur Top 15!
    output = {"total_projects": len(projects), "with_descriptions": with_desc, "profiles": {}}
    for name, matches in results.items():
        sorted_matches = sort_matches(matches)
        output["profiles"][name] = {
            "count": len(matches),
            "hot": sum(1 for m in matches if m["score"] >= 70),
            "ai_count": sum(1 for m in matches if m["is_ai"]),
            "top": sorted_matches[:30]  # Jetzt 30 statt 15!
        }
    
    with open("output/matches.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print("\n✅ Saved to output/matches.json (top 30 per profile)")

if __name__ == "__main__":
    main()
