#!/usr/bin/env python3
"""
Scan every website in the CSV for physical retail signals.
Checks main page + key subpages for addresses, store hours, location pages, etc.
"""

import asyncio
import aiohttp
import csv
import json
import re
import ssl
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

INPUT_CSV = '/home/ubuntu/.cursor/projects/workspace/uploads/potential_retail_-_Sheet1__1_.csv'
OUTPUT_JSON = '/workspace/scan_results.json'

RETAIL_SUBPAGES = [
    '', # home page
    '/pages/locations',
    '/pages/location',
    '/pages/stores',
    '/pages/store',
    '/pages/visit-us',
    '/pages/visit',
    '/pages/our-stores',
    '/pages/our-locations',
    '/pages/our-space',
    '/pages/our-facilities',
    '/pages/find-us',
    '/pages/find-a-store',
    '/pages/store-locator',
    '/pages/contact-us',
    '/pages/contact',
    '/pages/about-us',
    '/pages/about',
    '/pages/showroom',
    '/pages/gallery',
    '/pages/hours',
    '/pages/store-hours',
]

RETAIL_SIGNAL_PATTERNS = [
    # Address patterns (US/CA street addresses)
    r'\d{1,5}\s+(?:N\.?|S\.?|E\.?|W\.?|North|South|East|West|NW|NE|SW|SE)?\s*(?:[A-Z][a-z]+\s*){1,4}(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Rd|Road|Dr(?:ive)?|Ln|Lane|Way|Pl(?:ace)?|Ct|Court|Pkwy|Parkway|Hwy|Highway)\b',
    # Zip codes in context
    r'[A-Z]{2}\s+\d{5}(?:-\d{4})?',
    # Canadian postal codes
    r'[A-Z]\d[A-Z]\s*\d[A-Z]\d',
    # Store hours patterns
    r'(?:Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)\s*[-–:]\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|[0-9])',
    r'\d{1,2}\s*(?::|\.)\s*\d{2}\s*(?:am|pm|AM|PM)\s*[-–]\s*\d{1,2}\s*(?::|\.)\s*\d{2}\s*(?:am|pm|AM|PM)',
    r'\d{1,2}\s*(?:am|pm|AM|PM)\s*[-–]\s*\d{1,2}\s*(?:am|pm|AM|PM)',
    # Phone numbers (US format)
    r'\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}',
]

RETAIL_KEYWORDS = [
    'visit us', 'visit our', 'come visit', 'come see us', 'stop by',
    'our store', 'our shop', 'our showroom', 'our gallery', 'our studio',
    'our location', 'our locations', 'our facilities',
    'store hours', 'shop hours', 'gallery hours', 'showroom hours', 'business hours', 'hours of operation',
    'store location', 'store address',
    'walk-in', 'walk in', 'walkins', 'walk-ins welcome',
    'open monday', 'open tuesday', 'open daily', 'open 7 days',
    'mon-fri', 'mon-sat', 'mon - fri', 'mon - sat', 'monday-friday', 'monday-saturday',
    'in-store', 'in store pickup', 'curbside pickup',
    'find us', 'find a store', 'find our store',
    'directions', 'get directions',
    'located at', 'located in', 'we are located',
    'flagship', 'showroom', 'gallery', 'tasting room', 'taproom', 'café', 'cafe',
    'bakery', 'farm stand', 'farm store',
    'schedule a visit', 'book a visit', 'make an appointment',
    'warehouse showroom', 'open to the public',
]

EXCLUSION_KEYWORDS = [
    'wholesale only', 'trade only', 'b2b only',
    'we do not have a physical', 'no physical location',
    'online only', 'online-only store', 'we are an online',
    'no storefront', 'no retail location',
]

BANNED_PATTERNS = [
    r'\bvape[s]?\b', r'\bvaping\b', r'\bcannabis\b', r'\bthc\b', r'\bhhc\b',
    r'kratom', r'\bnicotine\b', r'\bdabbing\b',
]

WHOLESALE_PATTERNS = [
    r'\bwholesale\b', r'\bb2b\b', r'\bdistribut',
    r'wholesale\.', r'b2b\.',
]

TEST_PATTERNS = [r'\btest\b', r'\bsandbox\b', r'\bdemo\b']


def has_pattern(text, patterns):
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def normalize_url(web):
    web = web.strip().rstrip('/')
    if not web.startswith('http'):
        web = 'https://' + web
    return web


def analyze_html(html_text, url):
    """Analyze HTML content for retail signals."""
    signals = {
        'addresses': [],
        'hours_found': False,
        'keywords_found': [],
        'exclusion_found': [],
        'phone_numbers': [],
        'has_location_page_link': False,
    }

    if not html_text:
        return signals

    text = html_text.lower()
    soup = BeautifulSoup(html_text, 'lxml')
    visible_text = soup.get_text(separator=' ', strip=True).lower()

    for kw in RETAIL_KEYWORDS:
        if kw in visible_text:
            signals['keywords_found'].append(kw)

    for kw in EXCLUSION_KEYWORDS:
        if kw in visible_text:
            signals['exclusion_found'].append(kw)

    for pat in RETAIL_SIGNAL_PATTERNS:
        matches = re.findall(pat, html_text, re.IGNORECASE)
        if matches:
            if 'am' in pat.lower() or 'mon' in pat.lower() or 'AM' in pat:
                signals['hours_found'] = True
            elif 'zip' in str(pat) or r'[A-Z]{2}' in pat or r'[A-Z]\d[A-Z]' in pat:
                for m in matches[:5]:
                    signals['addresses'].append(m.strip())
            elif r'\d{3}' in pat:
                for m in matches[:3]:
                    signals['phone_numbers'].append(m.strip())
            else:
                for m in matches[:5]:
                    signals['addresses'].append(m.strip())

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].lower()
        link_text = a_tag.get_text(strip=True).lower()
        location_terms = ['location', 'store', 'visit', 'find-us', 'find-a-store',
                          'showroom', 'gallery', 'our-space', 'our-facilities', 'hours']
        for term in location_terms:
            if term in href or term in link_text:
                signals['has_location_page_link'] = True
                break

    return signals


async def fetch_page(session, url, timeout=12):
    """Fetch a single page, return HTML or None."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                               allow_redirects=True, ssl=False) as resp:
            if resp.status == 200:
                ct = resp.headers.get('content-type', '')
                if 'text/html' in ct or 'text/' in ct:
                    return await resp.text(errors='replace')
            return None
    except Exception:
        return None


async def scan_business(session, name, web, semaphore):
    """Scan a single business website for retail signals."""
    async with semaphore:
        base_url = normalize_url(web)
        combined_signals = {
            'addresses': set(),
            'hours_found': False,
            'keywords_found': set(),
            'exclusion_found': set(),
            'phone_numbers': set(),
            'has_location_page_link': False,
            'pages_checked': 0,
            'pages_responded': 0,
            'subpages_with_signals': [],
        }

        for subpage in RETAIL_SUBPAGES:
            url = base_url.rstrip('/') + subpage
            html = await fetch_page(session, url)
            combined_signals['pages_checked'] += 1

            if html:
                combined_signals['pages_responded'] += 1
                signals = analyze_html(html, url)

                combined_signals['addresses'].update(signals['addresses'])
                if signals['hours_found']:
                    combined_signals['hours_found'] = True
                combined_signals['keywords_found'].update(signals['keywords_found'])
                combined_signals['exclusion_found'].update(signals['exclusion_found'])
                combined_signals['phone_numbers'].update(signals['phone_numbers'])
                if signals['has_location_page_link']:
                    combined_signals['has_location_page_link'] = True

                if signals['keywords_found'] or signals['addresses'] or signals['hours_found']:
                    combined_signals['subpages_with_signals'].append(subpage or '/')

        score = 0
        strong_kw = {'visit us', 'visit our', 'come visit', 'our store', 'our shop',
                     'our showroom', 'our gallery', 'our studio', 'our location',
                     'our locations', 'store hours', 'showroom hours', 'gallery hours',
                     'hours of operation', 'store location', 'store address',
                     'walk-in', 'walk-ins welcome', 'in-store', 'curbside pickup',
                     'in store pickup', 'find a store', 'located at', 'located in',
                     'we are located', 'showroom', 'gallery', 'tasting room',
                     'taproom', 'bakery', 'cafe', 'café', 'farm stand', 'farm store',
                     'schedule a visit', 'book a visit', 'warehouse showroom',
                     'open to the public', 'our facilities', 'flagship',
                     'come see us', 'stop by', 'open daily', 'open 7 days'}

        medium_kw = {'find us', 'directions', 'get directions', 'business hours',
                     'mon-fri', 'mon-sat', 'mon - fri', 'mon - sat',
                     'monday-friday', 'monday-saturday', 'open monday', 'open tuesday',
                     'shop hours', 'make an appointment'}

        found_strong = combined_signals['keywords_found'] & strong_kw
        found_medium = combined_signals['keywords_found'] & medium_kw

        score += len(found_strong) * 3
        score += len(found_medium) * 1
        if combined_signals['hours_found']:
            score += 5
        if combined_signals['addresses']:
            score += 4
        if combined_signals['has_location_page_link']:
            score += 3
        if combined_signals['exclusion_found']:
            score -= 10

        result = {
            'name': name,
            'web': web,
            'score': score,
            'addresses_found': len(combined_signals['addresses']),
            'hours_found': combined_signals['hours_found'],
            'strong_keywords': sorted(found_strong),
            'medium_keywords': sorted(found_medium),
            'exclusion_keywords': sorted(combined_signals['exclusion_found']),
            'has_location_link': combined_signals['has_location_page_link'],
            'pages_responded': combined_signals['pages_responded'],
            'subpages_with_signals': combined_signals['subpages_with_signals'],
            'sample_addresses': sorted(combined_signals['addresses'])[:5],
            'sample_phones': sorted(combined_signals['phone_numbers'])[:3],
        }
        return result


async def main():
    rows = []
    seen = set()
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Business Name', '').strip()
            web = row.get('Web Address', '').strip()
            dedup = web.lower().replace('www.', '').rstrip('/')
            if dedup in seen:
                continue
            seen.add(dedup)

            combined = f"{name} {web}".lower()
            if has_pattern(combined, BANNED_PATTERNS):
                continue
            if has_pattern(combined, WHOLESALE_PATTERNS):
                continue
            if has_pattern(combined, TEST_PATTERNS):
                continue

            rows.append((name, web))

    print(f"Scanning {len(rows)} businesses...")

    semaphore = asyncio.Semaphore(30)
    connector = aiohttp.TCPConnector(limit=30, ssl=False)
    timeout = aiohttp.ClientTimeout(total=15)

    results = []
    batch_size = 50

    async with aiohttp.ClientSession(connector=connector, timeout=timeout,
                                      headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) as session:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            tasks = [scan_business(session, name, web, semaphore) for name, web in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in batch_results:
                if isinstance(r, Exception):
                    continue
                results.append(r)

            done = min(i + batch_size, len(rows))
            print(f"  Scanned {done}/{len(rows)} businesses...")
            await asyncio.sleep(0.5)

    results.sort(key=lambda x: x['score'], reverse=True)

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    flagged = [r for r in results if r['score'] >= 6]
    print(f"\nResults saved to {OUTPUT_JSON}")
    print(f"Total scanned: {len(results)}")
    print(f"Flagged with retail signals (score >= 6): {len(flagged)}")
    print(f"\nTop 50 by retail signal score:")
    for r in results[:50]:
        kws = ', '.join(r['strong_keywords'][:3])
        print(f"  [{r['score']:3d}] {r['name'][:45]:<45} | {r['web'][:35]:<35} | kw: {kws}")

    print(f"\nSignal distribution:")
    for threshold in [20, 15, 10, 6, 3, 1, 0]:
        count = len([r for r in results if r['score'] >= threshold])
        print(f"  Score >= {threshold:2d}: {count} businesses")


if __name__ == '__main__':
    asyncio.run(main())
