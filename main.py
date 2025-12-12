# -*- coding: utf-8 -*-
import time
import re
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
AGENCY_NAME = "Crown Travel Agency"
OUTPUT_FILE = "index.html" # Important: GitHub Pages looks for index.html

# FALLBACKS
VIRGIN_FALLBACK = "Reach out and we’ll quote some exclusive deals!"
CARNIVAL_FALLBACK = "Great rates & reduced deposits available - ask for a quote!"
DEFAULT_FALLBACK = "Check website for latest details."

# STAGE 1: FAST TARGETS
FAST_TARGETS = [
    {'Name': 'Royal Caribbean', 'URL': 'https://www.royalcaribbean.com/cruise-deals', 'Keywords': ['onboard credit', 'kids sail free', '30% off', '60% off', 'savings']},
    {'Name': 'Celebrity', 'URL': 'https://www.celebritycruises.com/cruise-deals', 'Keywords': ['75% off', 'bogo', 'onboard credit', 'drinks included']},
    {'Name': 'Princess', 'URL': 'https://www.princess.com/cruise-deals-promotions/', 'Keywords': ['40% off', '50% off', 'free upgrade', 'onboard spending']},
    {'Name': 'Virgin Voyages', 'URL': 'https://www.virginvoyages.com/cruise-deals', 'Keywords': ['off all voyages', 'sailor loot', 'bar tab'], 'Exclude': ['Special Discounts', 'Tailored for All', 'sign up']}
]

# STAGE 2: SLOW TARGETS
SLOW_TARGETS = [
    {'Name': 'Disney Cruise Line', 'URL': 'https://disneycruise.disney.go.com/special-offers/', 'Type': 'Disney'},
    {'Name': 'Carnival', 'URL': 'https://www.carnival.com/cruise-deals', 'Type': 'Carnival'}
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
final_results = {}

def run_scraper():
    print("🚀 STARTING AUTOMATED SCRAPE...")
    
    # --- STAGE 1 ---
    for target in FAST_TARGETS:
        try:
            r = requests.get(target['URL'], headers=HEADERS, timeout=10)
            if r.status_code == 200:
                if "Virgin" in target['Name']:
                    deal = extract_virgin_deal(r.text)
                else:
                    deal = extract_text_deal(r.text, target['Keywords'], target.get('Exclude', []))
                final_results[target['Name']] = deal
            else:
                final_results[target['Name']] = DEFAULT_FALLBACK
        except:
            final_results[target['Name']] = "Connection Failed"

    # --- STAGE 2 (SELENIUM HEADLESS) ---
    print("🚀 STARTING SELENIUM...")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Invisible mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    for target in SLOW_TARGETS:
        try:
            driver.get(target['URL'])
            time.sleep(8) # Wait for JS
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            deal = DEFAULT_FALLBACK

            if target['Type'] == 'Disney':
                items = soup.find_all(class_=lambda x: x and 'card-name' in x)
                valid = [i.get_text(strip=True) for i in items if "Canadian" not in i.get_text()]
                if valid: deal = valid[0]
                if len(valid) > 1: deal += f" (+ {len(valid)-1} others)"

            elif target['Type'] == 'Carnival':
                text = soup.get_text(" ", strip=True)
                deal = extract_carnival_logic(text)

            final_results[target['Name']] = deal
        except:
            final_results[target['Name']] = DEFAULT_FALLBACK

    driver.quit()
    generate_html()

# --- HELPER FUNCTIONS (Same logic as before) ---
def extract_virgin_deal(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(" ", strip=True)
        loot = re.search(r'\$[\d,]+\s*(?:in)?\s*Sailor Loot', text, re.IGNORECASE)
        percent = re.search(r'\d+%\s*off\s*(?:2nd|second)\s*sailor', text, re.IGNORECASE)
        deals = []
        if percent: deals.append(percent.group(0))
        if loot: deals.append(loot.group(0))
        return " + ".join(deals) if deals else VIRGIN_FALLBACK
    except: return VIRGIN_FALLBACK

def extract_text_deal(html, keywords, excludes):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        candidates = soup.find_all(['h1', 'h2', 'h3', 'h4', 'p'])
        best_match = None
        for tag in candidates:
            text = " ".join(tag.get_text().split()).strip()
            if len(text) < 5 or len(text) > 150: continue
            if any(exc.lower() in text.lower() for exc in excludes): continue
            for k in keywords:
                if k.lower() in text.lower():
                    if re.search(r'[\$%\d]', text): return text 
                    if best_match is None: best_match = text 
        return best_match if best_match else DEFAULT_FALLBACK
    except: return "Parse error."

def extract_carnival_logic(text):
    save = re.search(r'Save\s*up\s*to\s*\$[\d,]+', text, re.IGNORECASE)
    pct = re.search(r'Up\s*to\s*\d+%\s*off', text, re.IGNORECASE)
    obc = re.search(r'Up\s*to\s*\$[\d,]+\s*onboard', text, re.IGNORECASE)
    found = [m.group(0) for m in [save, pct, obc] if m]
    return " + ".join(found[:2]) if found else CARNIVAL_FALLBACK

def generate_html():
    # Generate Social Text for Javascript Copy
    social_text = f"🌎 ULTIMATE CRUISE UPDATE - {AGENCY_NAME} 🌎\\n\\n"
    order = ['Royal Caribbean', 'Celebrity', 'Disney Cruise Line', 'Virgin Voyages', 'Princess', 'Carnival']
    
    html_cards = ""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    for name in order:
        deal = final_results.get(name, DEFAULT_FALLBACK)
        social_text += f"🚢 {name.upper()}\\n• {deal}\\n\\n"
        
        color = "#003087"
        if "Virgin" in name: color = "#cc0000"
        if "Disney" in name: color = "#192f5e"
        if "Celebrity" in name: color = "#1a1a1a"
        
        html_cards += f"""
        <div class="card">
            <div class="card-header" style="background-color: {color}">
                <span class="line-name">{name}</span>
            </div>
            <div class="card-body">
                <h3>{deal}</h3>
            </div>
        </div>"""
    
    social_text += "👉 Message us to book ANY of these lines!"

    # FINAL HTML TEMPLATE
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Crown Travel Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f0f2f5; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            h1 {{ color: #333; margin: 0; }}
            .timestamp {{ color: #666; font-size: 0.9em; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
            .card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .card-header {{ padding: 15px; color: white; font-weight: bold; }}
            .card-body {{ padding: 20px; }}
            h3 {{ margin: 0; font-size: 1.1em; color: #444; line-height: 1.4; }}
            .copy-section {{ max-width: 600px; margin: 0 auto 30px auto; text-align: center; }}
            button {{ background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 1em; transition: 0.2s; }}
            button:hover {{ background: #0056b3; }}
            button:active {{ transform: scale(0.98); }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>👑 Crown Travel Command Center</h1>
            <p class="timestamp">Last Updated: {timestamp}</p>
        </div>

        <div class="copy-section">
            <button onclick="copyCaption()">📋 Copy Social Media Caption</button>
        </div>

        <div class="grid">
            {html_cards}
        </div>

        <script>
            function copyCaption() {{
                const text = "{social_text}";
                navigator.clipboard.writeText(text).then(() => {{
                    alert("Caption copied to clipboard!");
                }}).catch(err => {{
                    console.error('Failed to copy: ', err);
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_html)
    print("✅ HTML Generated.")

if __name__ == '__main__':
    run_scraper()
