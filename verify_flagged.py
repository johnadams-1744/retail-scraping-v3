#!/usr/bin/env python3
"""
Takes the scan results and builds a verification queue.
For each flagged business, attempts to fetch the specific location/contact pages
to extract actual addresses and confirm physical retail.
"""

import asyncio
import aiohttp
import csv
import json
import re
from bs4 import BeautifulSoup

SCAN_JSON = '/workspace/scan_results.json'
OUTPUT_JSON = '/workspace/verified_retail.json'
SCORE_THRESHOLD = 10

LOCATION_PAGES = [
    '/pages/locations', '/pages/location', '/pages/stores', '/pages/store',
    '/pages/visit-us', '/pages/visit', '/pages/our-stores', '/pages/our-locations',
    '/pages/our-space', '/pages/our-facilities', '/pages/find-us',
    '/pages/find-a-store', '/pages/store-locator', '/pages/contact-us',
    '/pages/contact', '/pages/showroom', '/pages/gallery', '/pages/hours',
    '/pages/store-hours', '/pages/about-us', '/pages/about',
]

US_STATE_ABBRS = r'(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)'
CA_PROV_ABBRS = r'(?:AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)'

ADDRESS_PATTERNS = [
    # Full US address: number + street + city + state + zip
    re.compile(r'\d{1,5}\s+[\w\s\.]+(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Rd|Road|Dr(?:ive)?|Ln|Lane|Way|Pl(?:ace)?|Ct|Court|Pkwy|Parkway|Hwy|Highway)[,\s]+[\w\s]+[,\s]+' + US_STATE_ABBRS + r'\s+\d{5}', re.IGNORECASE),
    # US state + zip
    re.compile(US_STATE_ABBRS + r'\s+\d{5}(?:-\d{4})?'),
    # Canadian postal code
    re.compile(r'[A-Z]\d[A-Z]\s*\d[A-Z]\d'),
    # Street address without full context
    re.compile(r'\d{1,5}\s+(?:N\.?|S\.?|E\.?|W\.?\s)?[\w\s\.]{2,30}(?:Street|Avenue|Boulevard|Road|Drive|Lane|Way|Place|Court|Parkway|Highway|St\.|Ave\.|Blvd\.|Rd\.|Dr\.|Ln\.|Ct\.)', re.IGNORECASE),
]

HOURS_PATTERNS = [
    re.compile(r'(?:Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)\s*[-–:]\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|\d)', re.IGNORECASE),
    re.compile(r'\d{1,2}\s*(?::|\.)\s*\d{2}\s*(?:am|pm)\s*[-–]\s*\d{1,2}\s*(?::|\.)\s*\d{2}\s*(?:am|pm)', re.IGNORECASE),
    re.compile(r'\d{1,2}\s*(?:am|pm)\s*[-–to]+\s*\d{1,2}\s*(?:am|pm)', re.IGNORECASE),
]

STRONG_LOCATION_KEYWORDS = [
    'visit us', 'visit our store', 'visit our shop', 'our location',
    'our locations', 'our showroom', 'our gallery', 'our studio',
    'store hours', 'gallery hours', 'showroom hours', 'hours of operation',
    'store location', 'located at', 'we are located', 'come visit',
    'walk-ins welcome', 'walk-in', 'in-store pickup', 'curbside pickup',
    'open monday', 'open daily', 'open 7 days',
    'schedule a visit', 'book a visit', 'open to the public',
]

EXCLUSION_SIGNALS = [
    'online only', 'online-only', 'we are an online', 'no physical location',
    'no storefront', 'wholesale only', 'b2b only', 'trade only',
]


def normalize_url(web):
    web = web.strip().rstrip('/')
    if not web.startswith('http'):
        web = 'https://' + web
    return web


async def fetch_page(session, url, timeout=12):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                               allow_redirects=True, ssl=False) as resp:
            if resp.status == 200:
                ct = resp.headers.get('content-type', '')
                if 'text/html' in ct or 'text/' in ct:
                    return await resp.text(errors='replace')
    except Exception:
        pass
    return None


def extract_location_info(html):
    """Extract detailed location information from an HTML page."""
    if not html:
        return None

    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text(separator='\n', strip=True)
    text_lower = text.lower()

    info = {
        'addresses': [],
        'has_hours': False,
        'has_strong_keywords': [],
        'has_exclusion': [],
        'raw_address_matches': [],
    }

    for pat in ADDRESS_PATTERNS:
        for m in pat.finditer(text):
            addr = m.group().strip()
            if len(addr) > 10 and addr not in info['raw_address_matches']:
                info['raw_address_matches'].append(addr)

    for pat in HOURS_PATTERNS:
        if pat.search(text):
            info['has_hours'] = True
            break

    for kw in STRONG_LOCATION_KEYWORDS:
        if kw in text_lower:
            info['has_strong_keywords'].append(kw)

    for kw in EXCLUSION_SIGNALS:
        if kw in text_lower:
            info['has_exclusion'].append(kw)

    # Try to count distinct locations by looking for unique state+zip combos
    state_zips = set()
    state_zip_pat = re.compile(US_STATE_ABBRS + r'\s+(\d{5})', re.IGNORECASE)
    for m in state_zip_pat.finditer(text):
        state_zips.add(m.group().strip().upper())

    ca_postals = set()
    ca_pat = re.compile(r'[A-Z]\d[A-Z]\s*\d[A-Z]\d')
    for m in ca_pat.finditer(text):
        ca_postals.add(m.group().strip().upper())

    info['unique_state_zips'] = sorted(state_zips)
    info['unique_ca_postals'] = sorted(ca_postals)
    info['estimated_locations'] = len(state_zips) + len(ca_postals)

    return info


async def verify_business(session, biz, semaphore):
    """Deep-verify a single business for physical retail."""
    async with semaphore:
        base_url = normalize_url(biz['web'])
        all_info = {
            'name': biz['name'],
            'web': biz['web'],
            'scan_score': biz['score'],
            'all_addresses': [],
            'all_state_zips': set(),
            'all_ca_postals': set(),
            'has_hours': False,
            'strong_keywords': set(),
            'exclusion_signals': set(),
            'pages_with_data': [],
            'confirmed_retail': False,
            'estimated_locations': 0,
        }

        for subpage in LOCATION_PAGES:
            url = base_url.rstrip('/') + subpage
            html = await fetch_page(session, url)
            if html:
                info = extract_location_info(html)
                if info:
                    if info['raw_address_matches'] or info['has_hours'] or info['has_strong_keywords']:
                        all_info['pages_with_data'].append(subpage)

                    all_info['all_addresses'].extend(info['raw_address_matches'])
                    all_info['all_state_zips'].update(info['unique_state_zips'])
                    all_info['all_ca_postals'].update(info['unique_ca_postals'])
                    if info['has_hours']:
                        all_info['has_hours'] = True
                    all_info['strong_keywords'].update(info['has_strong_keywords'])
                    all_info['exclusion_signals'].update(info['has_exclusion'])

        unique_addrs = list(set(all_info['all_addresses']))
        unique_zips = sorted(all_info['all_state_zips'])
        unique_ca = sorted(all_info['all_ca_postals'])

        loc_count = max(len(unique_zips), len(unique_ca))
        if loc_count == 0 and unique_addrs:
            loc_count = 1

        has_retail_signals = (
            all_info['has_hours'] and
            len(unique_addrs) > 0 and
            len(all_info['strong_keywords']) > 0
        )

        has_strong_retail = (
            all_info['has_hours'] and
            len(unique_addrs) > 0 and
            any(kw in all_info['strong_keywords'] for kw in [
                'visit us', 'visit our store', 'visit our shop',
                'our location', 'our locations', 'our showroom', 'our gallery',
                'store hours', 'gallery hours', 'showroom hours',
                'store location', 'located at', 'we are located',
                'come visit', 'walk-ins welcome', 'in-store pickup',
                'curbside pickup', 'open to the public', 'schedule a visit',
            ])
        )

        # Even without hours, a location page with addresses + strong keywords counts
        if not has_retail_signals and len(unique_addrs) > 0 and len(all_info['strong_keywords']) >= 2:
            has_retail_signals = True

        if all_info['exclusion_signals']:
            has_retail_signals = False
            has_strong_retail = False

        all_info['confirmed_retail'] = has_retail_signals or has_strong_retail
        all_info['estimated_locations'] = max(loc_count, 1) if all_info['confirmed_retail'] else 0

        return {
            'name': all_info['name'],
            'web': all_info['web'],
            'scan_score': all_info['scan_score'],
            'confirmed_retail': all_info['confirmed_retail'],
            'has_strong_retail': has_strong_retail,
            'estimated_locations': all_info['estimated_locations'],
            'unique_addresses': unique_addrs[:10],
            'unique_state_zips': unique_zips[:10],
            'unique_ca_postals': unique_ca[:5],
            'has_hours': all_info['has_hours'],
            'strong_keywords': sorted(all_info['strong_keywords']),
            'exclusion_signals': sorted(all_info['exclusion_signals']),
            'pages_with_data': all_info['pages_with_data'],
        }


async def main():
    with open(SCAN_JSON) as f:
        all_results = json.load(f)

    flagged = [r for r in all_results if r['score'] >= SCORE_THRESHOLD]
    print(f"Verifying {len(flagged)} businesses with scan score >= {SCORE_THRESHOLD}...")

    semaphore = asyncio.Semaphore(25)
    connector = aiohttp.TCPConnector(limit=25, ssl=False)

    results = []
    batch_size = 40

    async with aiohttp.ClientSession(connector=connector,
                                      headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) as session:
        for i in range(0, len(flagged), batch_size):
            batch = flagged[i:i+batch_size]
            tasks = [verify_business(session, biz, semaphore) for biz in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in batch_results:
                if isinstance(r, Exception):
                    continue
                results.append(r)

            done = min(i + batch_size, len(flagged))
            print(f"  Verified {done}/{len(flagged)}...")
            await asyncio.sleep(0.3)

    confirmed = [r for r in results if r['confirmed_retail']]
    confirmed.sort(key=lambda x: x['estimated_locations'], reverse=True)

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {OUTPUT_JSON}")
    print(f"Total verified: {len(results)}")
    print(f"Confirmed retail: {len(confirmed)}")
    print(f"\nAll confirmed retail businesses:")
    for r in confirmed:
        strong = r['has_strong_retail']
        locs = r['estimated_locations']
        kws = ', '.join(r['strong_keywords'][:3])
        addrs = '; '.join(r['unique_addresses'][:2])[:60]
        marker = '***' if strong else '   '
        print(f"  {marker} [{locs} loc] {r['name'][:40]:<40} | {r['web'][:32]:<32} | {addrs}")


if __name__ == '__main__':
    asyncio.run(main())
