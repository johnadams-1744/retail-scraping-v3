#!/usr/bin/env python3
"""
Build the final retail revenue predictions CSV using the three-phase funnel methodology.
Phase 1: Product eligibility (filter banned/wholesale/test)
Phase 2: Retail location verification (from website scanning pipeline)
Phase 3: Revenue prediction & ranking (benchmarks + foot traffic)

Output format:
Name, Website, Number of Retail Locations, Predicted Revenue, Product Type, Reasoning
"""

import csv
import json
import re
import math

INPUT_CSV = '/home/ubuntu/.cursor/projects/workspace/uploads/potential_retail_-_Sheet1__1_.csv'
SCAN_JSON = '/workspace/scan_results.json'
VERIFIED_JSON = '/workspace/verified_retail.json'
OUTPUT_CSV = '/workspace/retail_revenue_predictions.csv'

# ─── PHASE 1: ELIGIBILITY PATTERNS ───

BANNED_PRODUCT_PATTERNS = [
    (r'kratom', 'Kratom products'),
    (r'\bvape[s]?\b', 'Vaping products'),
    (r'\bvaping\b', 'Vaping products'),
    (r'fogervape', 'Vaping products'),
    (r'\be[-\s]?cig', 'E-cigarettes'),
    (r'\bthc\b', 'THC/Cannabis products'),
    (r'\bhhc\b', 'HHC/Cannabis products'),
    (r'\bcannabis\b', 'Cannabis products'),
    (r'\bnicotine\b', 'Nicotine products'),
    (r'\bdabbing\b', 'Drug paraphernalia'),
    (r'\bsmokin\b', 'Tobacco products'),
]

WHOLESALE_PATTERNS = [
    (r'\bwholesale\b', 'Wholesale/B2B only'),
    (r'\bb2b\b', 'B2B only'),
    (r'\bdistribut', 'Distributor only'),
    (r'wholesale\.', 'Wholesale portal'),
    (r'b2b\.', 'B2B portal'),
]

TEST_PATTERNS = [
    (r'\btest\b', 'Test store'),
    (r'\bsandbox\b', 'Sandbox store'),
    (r'\bdemo\b', 'Demo store'),
]

def check_patterns(text, patterns):
    t = text.lower()
    for pat, reason in patterns:
        if re.search(pat, t):
            return reason
    return None


# ─── PHASE 2 & 3: INDUSTRY / REVENUE LOGIC ───

def classify_industry(name, web, keywords, product_signals):
    n = (name + ' ' + web + ' ' + ' '.join(keywords) + ' ' + ' '.join(product_signals)).lower()

    if any(w in n for w in ['jewel', 'diamond', 'gem', 'gold ', 'platinum', 'ring ', 'necklace', 'gemstone']):
        return 'Luxury/Jewelry', 1250, 1500
    if any(w in n for w in ['boutique', 'apparel', 'fashion', 'clothing', 'shoe', 'boot',
                             'sneaker', 'athleisure', 'dress', 'lace ', 'leather goods',
                             'hat ', 'sock', 'lingerie', 'bikini', 'swim', 'locker',
                             'running', 'fitness']):
        return 'Specialty Apparel', 600, 850
    if any(w in n for w in ['furniture', 'mattress', 'rug', 'carpet', 'tile', 'marble',
                             'cabinet', 'vanity', 'home goods', 'home decor', 'cushion',
                             'patio', 'spa', 'hot tub', 'door', 'window', 'ceiling',
                             'floor', 'deck', 'display', 'iron accent', 'showroom',
                             'rarify', 'décor', 'decor']):
        return 'Furniture/Home Goods', 400, 550
    if any(w in n for w in ['gallery', 'fine art', 'art studio', 'painting', 'sculpture', 'beavis']):
        return 'Art Gallery/Fine Art', 350, 500
    if any(w in n for w in ['coffee', 'café', 'cafe', 'bakery', 'chocolate', 'candy',
                             'sweet', 'fudge', 'pie ', 'pastry', 'juice', 'tea ',
                             'popcorn', 'meat', 'butcher', 'sausage', 'food', 'kitchen',
                             'grocery', 'mart', 'market', 'deli', 'gourmet', 'praline',
                             'cioccolato', 'brew']):
        return 'Specialty Food/Beverage', 450, 600
    if any(w in n for w in ['hardware', 'supply', 'lumber', 'building', 'ladder',
                             'scaffold', 'industrial', 'tool', 'equipment']):
        return 'Hardware/Industrial Supply', 450, 600
    if any(w in n for w in ['gift', 'souvenir', 'general store', 'variety', 'emporium', 'gourd']):
        return 'Gift/Variety Retail', 450, 600
    if any(w in n for w in ['pet', 'animal', 'bird']):
        return 'Pet Supply', 450, 600
    if any(w in n for w in ['nursery', 'garden', 'plant', 'flower', 'floral', 'florist']):
        return 'Garden/Nursery/Florist', 450, 600
    if any(w in n for w in ['sport', 'outdoor', 'bike', 'cycle', 'skate', 'surf',
                             'tennis', 'golf', 'bowling', 'archery', 'fishing']):
        return 'Sporting Goods/Outdoor', 450, 600
    if any(w in n for w in ['music', 'instrument', 'guitar', 'record', 'vinyl']):
        return 'Musical Instruments/Media', 450, 600
    if any(w in n for w in ['auto', 'car ', 'motor', 'racing', 'performance', 'tuning']):
        return 'Automotive Parts/Accessories', 450, 600
    if any(w in n for w in ['safe', 'gun ', 'tactical', 'security', 'billiard', 'game room']):
        return 'Specialty Retail', 450, 600
    if any(w in n for w in ['adult', 'novelty', 'love shop', 'bachelorette']):
        return 'Adult Novelty/Wellness', 450, 600
    if any(w in n for w in ['wellness', 'spa ', 'beauty', 'skin', 'cosmetic']):
        return 'Beauty/Wellness', 450, 600

    return 'General Retail', 450, 600


def estimate_sqft(industry, name):
    n = name.lower()
    if 'furniture' in industry.lower() or 'home goods' in industry.lower():
        if any(w in n for w in ['warehouse', 'outlet', 'depot', 'express']):
            return 10000
        if 'rug' in n or 'gregorian' in n:
            return 40000
        if 'rarify' in n:
            return 15000
        return 5000
    if 'hardware' in industry.lower() or 'industrial' in industry.lower():
        if 'building' in n or 'lumber' in n:
            return 10000
        if 'ladder' in n:
            return 5000
        return 3000
    if 'nursery' in industry.lower() or 'garden' in industry.lower():
        return 8000
    if 'gift' in industry.lower() or 'variety' in industry.lower():
        return 2000
    if 'food' in industry.lower() or 'beverage' in industry.lower():
        return 1200
    if 'luxury' in industry.lower() or 'jewelry' in industry.lower():
        return 1500
    if 'apparel' in industry.lower():
        return 1500
    if 'art' in industry.lower() and 'gallery' in industry.lower():
        return 2000
    if 'pet' in industry.lower():
        return 2500
    if 'sporting' in industry.lower() or 'outdoor' in industry.lower():
        return 3000
    if 'adult' in industry.lower():
        return 1500
    if 'auto' in industry.lower():
        return 2000
    return 1500


def estimate_traffic(name, web, keywords, addresses):
    combined = (name + ' ' + web + ' ' + ' '.join(keywords) + ' ' + ' '.join(addresses)).lower()

    high_signals = ['flagship', 'broadway', 'rodeo', '5th ave', 'main st',
                    'beverly hills', 'soho', 'tourist', 'airport', 'mall',
                    'town centre', 'town center', 'shopping center',
                    'river street', 'columbus ave', 'park city', '5th avenue',
                    'north beach', 'little italy', 'pigeon forge']
    low_signals = ['warehouse', 'industrial', 'appointment', 'by appointment',
                   'schedule a visit', 'rural', 'destination', 'potato road']

    for s in high_signals:
        if s in combined:
            return 'High', 1.5
    for s in low_signals:
        if s in combined:
            return 'Low', 0.7
    return 'Medium', 1.0


def revenue_range(point_est):
    low = round(point_est * 0.6, -3)
    high = round(point_est * 1.4, -3)

    def fmt(v):
        if v >= 1_000_000:
            m = v / 1_000_000
            return f"${m:.1f}M" if m != int(m) else f"${int(m)}M"
        elif v >= 1000:
            return f"${int(v/1000)}K"
        else:
            return f"${int(v)}"

    return f"{fmt(low)}–{fmt(high)}"


# ─── MANUAL OVERRIDES (web-search verified) ───

MANUAL_OVERRIDES = {
    'and-sons.com': {'locations': 1, 'sqft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Luxury chocolate & café',
        'notes': '1 brand-owned store at 9548 Brighton Way, Beverly Hills CA (1 block off Rodeo Drive). Verified via and-sons.com/pages/visit-us.'},
    'store.thearmoury.com': {'locations': 4, 'sqft': 2000, 'traffic': 'High', 'traffic_mult': 1.5,
        'industry': 'Luxury/Jewelry', 'bench_low': 1250, 'bench_high': 1500,
        'product_type': 'Luxury menswear & tailoring',
        'notes': '4 brand-owned locations (2 NYC: Tribeca + UES, 2 HK). Verified via thearmoury.com/faq.'},
    'www.riverstreetsweets.com': {'locations': 2, 'sqft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Pralines, candy & confections',
        'notes': '2 brand-owned stores on River St & Broughton St, Savannah GA (tourist district). Verified via riverstreetsweets.com/pages/find-your-store.'},
    'www.townshop.com': {'locations': 1, 'sqft': 2500, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Luxury lingerie & intimate apparel',
        'notes': '1 brand-owned store at 2270 Broadway, NYC (est 1888). Verified via townshop.com/pages/our-store.'},
    'recreationsoutlet.com': {'locations': 1, 'sqft': 5000,
        'product_type': 'Outdoor play equipment & recreation',
        'notes': '1 brand-owned showroom at 484 W Olentangy St, Powell OH. Verified via recreationsoutlet.com/pages/contact-us.'},
    'lukeslocker.com': {'locations': 2, 'sqft': 3000,
        'industry': 'Specialty Apparel', 'bench_low': 600, 'bench_high': 850,
        'product_type': 'Running shoes & athletic apparel',
        'notes': '2 brand-owned stores in Dallas & Fort Worth TX. Verified via lukeslocker.com/pages/stores.'},
    'loftycoffee.com': {'locations': 6, 'sqft': 1200, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Specialty coffee, breakfast & lunch café',
        'notes': '6 brand-owned cafés across San Diego area. Verified via loftycoffee.com/pages/locations.'},
    'gritcoffee.com': {'locations': 5, 'sqft': 1200,
        'product_type': 'Specialty coffee, food, craft beer & wine',
        'notes': '5 active brand-owned cafés in Charlottesville VA. Verified via gritcoffee.com/pages/locations.'},
    'www.mannsjewelers.com': {'locations': 1, 'sqft': 3000,
        'industry': 'Luxury/Jewelry', 'bench_low': 1250, 'bench_high': 1500,
        'product_type': 'Designer jewelry, bridal & luxury watches',
        'notes': '1 brand-owned store at 2945 Monroe Ave, Rochester NY. Family-owned since 1947. Verified via mannsjewelers.com/pages/our-store.'},
    'gregorianrugs.com': {'locations': 1, 'sqft': 40000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'industry': 'Furniture/Home Goods', 'bench_low': 400, 'bench_high': 550,
        'product_type': 'Handmade oriental rugs & restoration services',
        'notes': '1 brand-owned 40,000 sq ft showroom (8 galleries) at 2284 Washington St, Newton Falls MA. Verified via gregorianrugs.com/pages/store-hours.'},
    'rarify.co': {'locations': 2, 'sqft': 15000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'industry': 'Furniture/Home Goods', 'bench_low': 400, 'bench_high': 550,
        'product_type': 'Vintage & contemporary furniture, lighting & design objects',
        'notes': '2 brand-owned locations: Philadelphia gallery (735 Bainbridge St) + ~30K sqft Lebanon County PA warehouse showroom. Verified via rarify.co/pages/our-space.'},
    'furnituredepot.ca': {'locations': 2, 'sqft': 8000, 'traffic': 'High', 'traffic_mult': 1.5,
        'industry': 'Furniture/Home Goods', 'bench_low': 400, 'bench_high': 550,
        'product_type': 'Home furniture & bedroom sets',
        'notes': '2 brand-owned showrooms in Mississauga ON (Heartland Town Centre + Dundas St W). Verified via furnituredepot.ca/pages/visit-us.'},
    'davidkbeavis.com': {'locations': 2, 'sqft': 2000, 'traffic': 'High', 'traffic_mult': 1.5,
        'industry': 'Art Gallery/Fine Art', 'bench_low': 350, 'bench_high': 500,
        'product_type': 'Fine art photography, prints & scarves',
        'notes': '2 brand-owned galleries: 314 Main St Park City UT + 491 5th Ave South Naples FL. Verified via davidkbeavis.com/pages/galleries.'},
    'www.giftcorral.com': {'locations': 5, 'sqft': 2000, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Montana-themed gifts, huckleberry products & souvenirs',
        'notes': '5 brand-owned locations across Montana (Downtown Bozeman, Walmart, Airport, Missoula, Lewis & Clark Caverns). Verified via giftcorral.com/pages/locations.'},
    'sarkispastry.com': {'locations': 3, 'sqft': 1500,
        'product_type': 'Middle Eastern & Armenian pastries, custom cakes',
        'notes': '3 brand-owned bakeries in Glendale, Pasadena, Anaheim CA. Verified via sarkispastry.com/pages/locations.'},
    'theanimalhouse.net': {'locations': 3, 'sqft': 2500,
        'product_type': 'Pet food, supplies & accessories',
        'notes': '3 brand-owned pet stores in Maine (Damariscotta, Westbrook, Brunswick). Verified via theanimalhouse.net/pages/locations.'},
    'www.mbgourds.com': {'locations': 1, 'sqft': 7000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'Handcrafted gourd art, gifts & home decor',
        'notes': '1 brand-owned 7,000 sq ft gift shop at 125 Potato Rd, Carlisle PA on a 200-acre farm. Verified via mbgourds.com/pages/visit-us.'},
    'americanladders.com': {'locations': 2, 'sqft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'Ladders, scaffolds & fall protection equipment',
        'notes': '2 brand-owned showroom/warehouses in Glastonbury CT & Milford CT. Verified via americanladders.com/pages/locations.'},
    'zcioccolato.com': {'locations': 1, 'sqft': 1200, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Gourmet fudge, truffles, gelato & candy',
        'notes': '1 brand-owned store at 474 Columbus Ave, San Francisco (North Beach). Verified via zcioccolato.com/pages/contact-us.'},
    'pigeonmountaintrading.com': {'locations': 1, 'sqft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'Beekeeping supplies & garden boutique items',
        'notes': '1 brand-owned store at 106 N Main St, LaFayette GA. Verified via pigeonmountaintrading.com/pages/about-us.'},
    'www.kincaidsmusic.com': {'locations': 1, 'sqft': 3000,
        'product_type': 'Band & orchestra instruments, rentals & repair',
        'notes': '1 brand-owned store at 1325 W 1st St, Springfield OH. Verified via kincaidsmusic.com/pages/contact-us.'},
    'shop.jessebrowns.com': {'locations': 1, 'sqft': 5000,
        'product_type': 'Outdoor apparel, fly-fishing & camping gear',
        'notes': '1 brand-owned store at 4732 Sharon Rd, Charlotte NC (est. 1970). Verified via jessebrowns.com/find-us/.'},
    'petalumapiecompany.com': {'locations': 1, 'sqft': 1000,
        'product_type': 'Farm-to-table pies & bakery café',
        'notes': '1 brand-owned bakery at 125 Petaluma Blvd N, Petaluma CA. Verified via petalumapiecompany.com/pages/contact.'},
    'josephsorganicbakery.com': {'locations': 1, 'sqft': 1200,
        'product_type': 'Organic ancient grain breads & vegan baked goods',
        'notes': '1 brand-owned bakery at 18228 W Dixie Hwy, North Miami Beach FL. Verified via veganbakerymiami.com/pages/contact-us.'},
    'allmarbletiles.com': {'locations': 1, 'sqft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'industry': 'Furniture/Home Goods', 'bench_low': 400, 'bench_high': 550,
        'product_type': 'Marble, tile & natural stone',
        'notes': '1 brand-owned showroom at 175 Moonachie Rd, Moonachie NJ. Verified via allmarbletiles.com/pages/about-us.'},
    'www.roosroast.com': {'locations': 2, 'sqft': 1200,
        'product_type': 'Specialty coffee & roastery café',
        'notes': '2 brand-owned locations in Ann Arbor MI (Rosewood + E Liberty St). Verified via roosroast.com.'},
    'blancgroup.com': {'locations': 2, 'sqft': 2000, 'traffic': 'High', 'traffic_mult': 1.5,
        'industry': 'Specialty Apparel', 'bench_low': 600, 'bench_high': 850,
        'product_type': 'Designer fashion, eyewear & skincare',
        'notes': '2 brand-owned stores (SoHo NYC flagship + Asia). Verified via press coverage.'},
    'mastshoes.com': {'locations': 1, 'sqft': 2000,
        'product_type': 'Comfort & orthopedic footwear',
        'notes': '1 brand-owned store at 2519 Jackson Ave, Ann Arbor MI with professional fitting. Verified via mastshoes.com/pages/visit-the-store.'},
    'loveshop.ca': {'locations': 24, 'sqft': 1500,
        'product_type': 'Adult novelty & wellness products',
        'notes': '24 brand-owned stores across Ontario. Verified via loveshop.ca location pages (24 unique postal codes).'},
    'papertrailrhinebeck.com': {'locations': 1, 'sqft': 1500,
        'product_type': 'Stationery, jewelry, home decor & gifts',
        'notes': '1 brand-owned store at 6423 Montgomery St, Rhinebeck NY. Verified via papertrailrhinebeck.com/pages/contact-us.'},
    'smgeneralstore.com': {'locations': 1, 'sqft': 2000, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Vintage gifts, antiques & homemade preserves',
        'notes': '1 brand-owned store at 139 E Wears Valley Rd, Pigeon Forge TN (tourist area). Verified via web search.'},
    'chihuly-garden-and-glass.myshopify.com': {'locations': 1, 'sqft': 2000, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Art books, prints, apparel & museum gifts',
        'notes': '1 brand-owned bookstore at 305 Harrison St, Seattle WA (Chihuly Garden & Glass). Verified via chihulygardenandglass.com/visit/bookstore.'},
    'www.baltimorebilliards.com': {'locations': 1, 'sqft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'Pool tables, cues & game room equipment',
        'notes': '1 brand-owned showroom at 8906 Waltham Woods Rd, Parkville MD. Verified via baltimorebilliards.com.'},
    'leilanisleis.com': {'locations': 2, 'sqft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Fresh flower leis, tropical gifts & café',
        'notes': '2 brand-owned locations in Las Vegas area. Verified via leilanisleis.com location pages.'},
    'libertysafeofcollegestation.com': {'locations': 1, 'sqft': 2500, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'Gun safes, vault doors & security storage',
        'notes': '1 brand-owned store at 1055 Texas Ave S, College Station TX. Verified via web search.'},
    'shopoxfordstreet.com': {'locations': 1, 'sqft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'product_type': 'Fashion apparel & accessories',
        'notes': '1 brand-owned store at BayFair Center, San Leandro CA (mall). Verified via web search.'},
    'www.mycuttinggarden.com': {'locations': 1, 'sqft': 1500,
        'product_type': 'Custom floral arrangements & plants',
        'notes': "1 brand-owned florist at 9039 Katy Freeway Suite 211, Houston TX. Voted Houston's Best Florist. Verified via mycuttinggarden.com/pages/contact-us."},
    'www.mattressinnovations.com': {'locations': 1, 'sqft': 5000,
        'industry': 'Furniture/Home Goods', 'bench_low': 400, 'bench_high': 550,
        'product_type': 'Mattresses & sleep products',
        'notes': '1 brand-owned showroom with posted visit hours. Verified via mattressinnovations.com.'},
    'guttercleaningbusiness.com': {'locations': 1, 'sqft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'Gutter cleaning equipment & SkyVac systems',
        'notes': '1 brand-owned showroom at 1000 N Horner Blvd, Sanford NC. Verified via guttercleaningbusiness.com/pages/about-us.'},
    'hpcbikes.com': {'locations': 1, 'sqft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'product_type': 'High-performance electric bikes',
        'notes': '1 brand-owned facility at 4180 Guardian St, Simi Valley CA with showroom. Verified via hpcbikes.com/pages/contact-us.'},
}

FALSE_POSITIVES = {
    'zipcushions.com', 'secretbargainshop.com', 'www.1800ceiling.com',
    'stickleyvirtualmarket.com', 'stickley-museum.myshopify.com',
}


def main():
    with open(SCAN_JSON) as f:
        scan_data = json.load(f)
    with open(VERIFIED_JSON) as f:
        verified_data = json.load(f)

    scan_by_web = {r['web'].lower().rstrip('/'): r for r in scan_data}
    verified_by_web = {r['web'].lower().rstrip('/'): r for r in verified_data}

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
            rows.append((name, web))

    phase1_eligible = []
    phase1_ineligible = []
    phase1_review = []
    output_rows = []

    # ─── PHASE 1: ELIGIBILITY SCREEN ───
    for name, web in rows:
        combined = f"{name} {web}"

        ban = check_patterns(combined, BANNED_PRODUCT_PATTERNS)
        if ban:
            phase1_ineligible.append((name, web, ban))
            output_rows.append({
                'Name': name, 'Website': web, 'Number of Retail Locations': 0,
                'Predicted Revenue': '', 'Product Type': ban,
                'Reasoning': f'INELIGIBLE — Prohibited products: {ban}. Not eligible for Shopify Payments.',
                '_phase': 1, '_rev': 0
            })
            continue

        ws = check_patterns(combined, WHOLESALE_PATTERNS)
        if ws:
            phase1_ineligible.append((name, web, ws))
            output_rows.append({
                'Name': name, 'Website': web, 'Number of Retail Locations': 0,
                'Predicted Revenue': '', 'Product Type': ws,
                'Reasoning': f'INELIGIBLE — {ws}: not a consumer-facing retail business.',
                '_phase': 1, '_rev': 0
            })
            continue

        ts = check_patterns(combined, TEST_PATTERNS)
        if ts:
            phase1_ineligible.append((name, web, ts))
            output_rows.append({
                'Name': name, 'Website': web, 'Number of Retail Locations': 0,
                'Predicted Revenue': '', 'Product Type': ts,
                'Reasoning': f'INELIGIBLE — {ts}: not a real business.',
                '_phase': 1, '_rev': 0
            })
            continue

        phase1_eligible.append((name, web))

    print(f"Phase 1 complete: {len(phase1_eligible)} eligible, {len(phase1_ineligible)} ineligible, {len(phase1_review)} review needed.")

    # ─── PHASE 2: RETAIL LOCATION VERIFICATION ───
    phase2_retail = []
    phase2_no_retail = []

    for name, web in phase1_eligible:
        web_key = web.lower().rstrip('/')
        web_lower = web.lower().rstrip('/')

        is_false_positive = any(fp in web_lower for fp in FALSE_POSITIVES)
        if is_false_positive:
            phase2_no_retail.append((name, web))
            s = scan_by_web.get(web_key)
            score = s['score'] if s else 0
            output_rows.append({
                'Name': name, 'Website': web, 'Number of Retail Locations': 0,
                'Predicted Revenue': '', 'Product Type': 'See website',
                'Reasoning': f'NO RETAIL — Website scanned (signal score: {score}). Retail signals detected but verified as non-retail (online-only portal or no public-facing storefront).',
                '_phase': 2, '_rev': 0
            })
            continue

        override = MANUAL_OVERRIDES.get(web_key) or MANUAL_OVERRIDES.get(web.lower().rstrip('/'))
        v = verified_by_web.get(web_key)
        s = scan_by_web.get(web_key)

        is_retail = False
        locations = 0

        if override:
            is_retail = True
            locations = override['locations']
        elif v and v['confirmed_retail']:
            is_retail = True
            locations = v['estimated_locations']

        if is_retail and locations > 0:
            phase2_retail.append((name, web, locations, override, v, s))
        else:
            phase2_no_retail.append((name, web))
            score = s['score'] if s else 0
            pages = s.get('pages_responded', 0) if s else 0
            output_rows.append({
                'Name': name, 'Website': web, 'Number of Retail Locations': 0,
                'Predicted Revenue': '', 'Product Type': 'See website',
                'Reasoning': f'NO RETAIL — Website scanned (signal score: {score}, {pages} pages responded). No confirmed brand-owned retail location found after checking homepage + location/contact/about/visit-us pages for addresses, store hours, and retail signals. Stockists and third-party retailers excluded.',
                '_phase': 2, '_rev': 0
            })

    print(f"Phase 2 complete: {len(phase2_retail)} businesses have brand-owned retail, {len(phase2_no_retail)} do not.")

    # ─── PHASE 3: REVENUE PREDICTION & RANKING ───
    phase3_rows = []

    for name, web, locations, override, v, s in phase2_retail:
        kws = []
        addrs = []
        if v:
            kws = v.get('strong_keywords', [])
            addrs = v.get('unique_addresses', [])
        elif s:
            kws = s.get('strong_keywords', [])

        if override:
            industry = override.get('industry', None)
            bench_low = override.get('bench_low', None)
            bench_high = override.get('bench_high', None)
            sqft = override.get('sqft', 1500)
            traffic = override.get('traffic', 'Medium')
            traffic_mult = override.get('traffic_mult', 1.0)
            product_type = override.get('product_type', 'See website')
            notes = override.get('notes', '')

            if not industry:
                industry, bl, bh = classify_industry(name, web, kws, [])
                if not bench_low: bench_low = bl
                if not bench_high: bench_high = bh
        else:
            product_type = 'See website'
            industry, bench_low, bench_high = classify_industry(name, web, kws, addrs)
            sqft = estimate_sqft(industry, name)
            traffic, traffic_mult = estimate_traffic(name, web, kws, addrs)
            addr_str = '; '.join(addrs[:3])[:80]
            pages = v.get('pages_with_data', []) if v else []
            page_str = ', '.join(pages[:3])
            notes = f"Website-verified: {addr_str}. Signal pages: {page_str}."

        avg_bench = (bench_low + bench_high) / 2
        point_est = locations * sqft * avg_bench * traffic_mult
        rev_range = revenue_range(point_est)

        confidence = 'Low'
        if override:
            confidence = 'Medium' if locations >= 2 else 'Medium'
        if sqft > 5000 or locations >= 3:
            confidence = 'Medium'
        if override and locations >= 5:
            confidence = 'High'

        reasoning = f"QUALIFIED — {notes} Revenue est: {locations} loc × {sqft:,} sqft × ${avg_bench:.0f}/sqft ({industry}) × {traffic_mult}x ({traffic} traffic)."

        phase3_rows.append({
            'Name': name, 'Website': web,
            'Number of Retail Locations': locations,
            'Predicted Revenue': f'{rev_range} ({confidence} confidence)',
            'Product Type': product_type,
            'Reasoning': reasoning,
            '_phase': 3, '_rev': point_est
        })

    phase3_rows.sort(key=lambda x: x['_rev'], reverse=True)

    for i, r in enumerate(phase3_rows, 1):
        r['_rank'] = i

    output_rows.extend(phase3_rows)
    output_rows.sort(key=lambda x: (-x['_phase'], -x['_rev']))

    # Final sort: Phase 3 (qualified) first by revenue desc, then Phase 2, then Phase 1
    qualified = [r for r in output_rows if r['_phase'] == 3]
    no_retail = [r for r in output_rows if r['_phase'] == 2]
    ineligible = [r for r in output_rows if r['_phase'] == 1]
    qualified.sort(key=lambda x: x['_rev'], reverse=True)

    final = qualified + no_retail + ineligible

    fieldnames = ['Name', 'Website', 'Number of Retail Locations',
                  'Predicted Revenue', 'Product Type', 'Reasoning']

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(final)

    total_rev = sum(r['_rev'] for r in qualified)
    print(f"\nPhase 3 complete: {len(qualified)} qualified leads ranked by revenue.")
    print(f"Total predicted revenue (point estimates): ${total_rev:,.0f}")
    print(f"\nFinal CSV: {OUTPUT_CSV}")
    print(f"  Total rows: {len(final)}")
    print(f"  Qualified (Phase 3): {len(qualified)}")
    print(f"  No Retail (Phase 2): {len(no_retail)}")
    print(f"  Ineligible (Phase 1): {len(ineligible)}")
    print(f"\nTop 20 qualified leads:")
    for r in qualified[:20]:
        print(f"  {r['Name'][:42]:<42} | {r['Number of Retail Locations']:>2} loc | {r['Predicted Revenue']:<35} | {r['Product Type'][:35]}")


if __name__ == '__main__':
    main()
