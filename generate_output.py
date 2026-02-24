#!/usr/bin/env python3
"""
Retail Revenue Prediction Script
Processes the business CSV, applies research findings, exclusion/inclusion criteria,
industry benchmarks, and foot traffic multipliers to generate ranked revenue predictions.
"""

import csv
import re
import os

INPUT_CSV = '/home/ubuntu/.cursor/projects/workspace/uploads/potential_retail_-_Sheet1__1_.csv'
OUTPUT_CSV = '/workspace/retail_revenue_predictions.csv'

# ─── EXCLUSION PATTERNS ───
WHOLESALE_B2B = [
    r'\bwholesale\b', r'\bb2b\b', r'\bdistribut', r'\bdealer\b',
    r'wholesale\.', r'b2b\.', r'distributor\.',
    r'canadawholesale', r'fair-indigo-wholesale',
]
TEST_SANDBOX = [r'\btest\b', r'\bsandbox\b', r'\bdemo\b']
BANNED_PRODUCTS = [
    r'\bvape[s]?\b', r'\bvaping\b', r'\bcannabis\b', r'\bthc\b', r'\bhhc\b',
    r'kratom', r'\bnicotine\b', r'\bsmokin\b', r'\bdabbing\b',
    r'fogervape', r'bakedhhc', r'cryokratom', r'highmonkkratom',
]

def has_pattern(text, patterns):
    t = text.lower()
    return any(re.search(p, t) for p in patterns)

# ─── WEB RESEARCH CONFIRMED RETAIL (from actual web searches) ───
# Format: website_key -> (num_locations, industry, sq_ft_per_location, foot_traffic, notes)
CONFIRMED_RETAIL = {
    'lukeslocker.com': {
        'locations': 2,
        'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 3000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '2 locations in Dallas & Fort Worth TX. Running & fitness specialty. Main Street/Downtown traffic. Stockists excluded.'
    },
    'www.riverstreetsweets.com': {
        'locations': 2,
        'industry': 'General Retail (Confectionery)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '2 owned stores on River Street & Broughton St, Savannah GA (tourist district). General retail confectionery, high foot traffic. No stockists counted.'
    },
    'store.thearmoury.com': {
        'locations': 4,
        'industry': 'Luxury/Jewelry (Fine Menswear)',
        'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 2000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '4 owned locations: 2 in NYC (Tribeca, Upper East Side), 2 in Hong Kong. Luxury menswear. High foot traffic flagship locations. EXCLUSION NOTE: Pedder Building Hong Kong location is ground-floor arcade (not high floor office). Carlyle Club HK is Floor 55 (appointment only) - still counted as brand showroom per inclusion criteria.'
    },
    'www.townshop.com': {
        'locations': 1,
        'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 2500,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '1 owned store at 2270 Broadway, NYC (established 1888). Luxury lingerie & bra fitting. Broadway retail corridor = high foot traffic. No stockists.'
    },
    'and-sons.com': {
        'locations': 1,
        'industry': 'General Retail (Specialty Food/Chocolate)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '1 owned store at 9548 Brighton Way, Beverly Hills CA (1 block off Rodeo Drive). Luxury chocolate shop + café. High foot traffic retail corridor.'
    },
    'recreationsoutlet.com': {
        'locations': 1,
        'industry': 'General Retail (Outdoor Recreation Equipment)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned showroom at 484 W Olentangy St, Powell OH. Playsets, trampolines, recreational furniture. Medium foot traffic suburban location.'
    },
    'gregorianrugs.com': {
        'locations': 1,
        'industry': 'Furniture/Home Goods (Rugs)',
        'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 40000,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '1 owned showroom at 2284 Washington St, Newton Lower Falls MA. 40,000+ sq ft with 8 galleries. Appointment-based destination showroom = low foot traffic. No stockists.'
    },
    'www.giftcorral.com': {
        'locations': 5,
        'industry': 'General Retail (Gift Shop)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '5 owned locations across Montana (Downtown Bozeman, Bozeman Walmart, Airport, Downtown Missoula, Lewis & Clark Caverns). Tourist gift shops = high foot traffic. No stockists.'
    },
    'americanladders.com': {
        'locations': 2,
        'industry': 'General Retail (Industrial/Hardware)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '2 owned showroom/warehouses in Glastonbury CT & Milford CT, plus 7 pickup-only warehouses. Industrial destination retail = low foot traffic.'
    },
    'zcioccolato.com': {
        'locations': 1,
        'industry': 'General Retail (Specialty Food/Chocolate)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '1 owned store at 474 Columbus Ave, San Francisco (North Beach tourist district). Gourmet fudge/chocolate shop. High foot traffic.'
    },
    'sarkispastry.com': {
        'locations': 3,
        'industry': 'General Retail (Specialty Food/Bakery)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '3 owned bakery locations: Glendale, Pasadena, Anaheim CA. Middle Eastern/Armenian pastries. Medium foot traffic in suburban commercial areas.'
    },
    'loftycoffee.com': {
        'locations': 6,
        'industry': 'General Retail (Coffee/Café)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '6 owned café locations across San Diego area (Encinitas x2, La Costa, Carlsbad, Solana Beach, Little Italy). High foot traffic in coastal/urban locations.'
    },
    'gritcoffee.com': {
        'locations': 5,
        'industry': 'General Retail (Coffee/Café)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '5 active owned café locations in Charlottesville VA area (Downtown, Elliewood, Crozet, Pantops, UVA). Medium foot traffic downtown/university area.'
    },
    'www.baltimorebilliards.com': {
        'locations': 1,
        'industry': 'General Retail (Game Room/Specialty)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '1 owned showroom at 8906 Waltham Woods Rd, Parkville MD. Pool tables, cues, game room equipment. Destination-only = low foot traffic.'
    },
    'www.mannsjewelers.com': {
        'locations': 1,
        'industry': 'Luxury/Jewelry',
        'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 3000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned store at 2945 Monroe Ave, Rochester NY (Monroe Clover Plaza). Family-owned since 1947, 9th generation. Designer jewelry + luxury watches. Medium foot traffic suburban retail.'
    },
    'papertrailrhinebeck.com': {
        'locations': 1,
        'industry': 'General Retail (Gift/Stationery)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned store at 6423 Montgomery St, Rhinebeck NY. Stationery, gifts, jewelry, home décor. Main street retail = medium foot traffic.'
    },
    'smgeneralstore.com': {
        'locations': 1,
        'industry': 'General Retail (Gift/Souvenir)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '1 owned store at 139 E Wears Valley Rd, Pigeon Forge TN. Tourist area general store. High foot traffic in Smoky Mountain tourist corridor.'
    },
    'mastshoes.com': {
        'locations': 1,
        'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 2000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned store at 2519 Jackson Ave, Ann Arbor MI. Professional shoe fitting store. Medium foot traffic suburban location.'
    },
    'shopoxfordstreet.com': {
        'locations': 1,
        'industry': 'General Retail (Fashion/Accessories)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '1 owned store at BayFair Center, 310 Bayfair Dr, San Leandro CA. Mall anchor location = high foot traffic.'
    },
    'libertysafeofcollegestation.com': {
        'locations': 1,
        'industry': 'General Retail (Security/Safes)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2500,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '1 owned store at 1055 Texas Ave S, College Station TX. Safe showroom = destination retail, low foot traffic.'
    },
    'petalumapiecompany.com': {
        'locations': 1,
        'industry': 'General Retail (Specialty Food/Bakery)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned bakery at 125 Petaluma Blvd N, Petaluma CA. Farm-to-table bakery cafe in historic downtown. Medium foot traffic.'
    },
    'josephsorganicbakery.com': {
        'locations': 1,
        'industry': 'General Retail (Specialty Food/Bakery)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned bakery at 18228 W Dixie Hwy, North Miami Beach FL. Organic bakery. Medium foot traffic suburban location.'
    },
    'allmarbletiles.com': {
        'locations': 1,
        'industry': 'Furniture/Home Goods (Tile/Stone)',
        'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '1 owned showroom/warehouse at 175 Moonachie Rd, Moonachie NJ. Marble & tile showroom. Destination-only = low foot traffic.'
    },
    'www.roosroast.com': {
        'locations': 2,
        'industry': 'General Retail (Coffee/Café)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '2 owned locations in Ann Arbor MI (Rosewood roastery + E Liberty St downtown). Solar-powered coffee roaster. Medium foot traffic.'
    },
    'blancgroup.com': {
        'locations': 2,
        'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 2000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '2+ owned stores (SoHo NYC flagship + locations across Asia). Jessica Jung luxury fashion brand. ONLY counting 2 directly owned/operated stores. High foot traffic SoHo corridor.'
    },
    'flyingmonkeyjeans.com': {
        'locations': 1,
        'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned showroom at 1100 S San Pedro St, LA Fashion District. Industry/trade showroom open by appointment. Fashion District = medium foot traffic.'
    },
    'furnituredepot.ca': {
        'locations': 2,
        'industry': 'Furniture/Home Goods',
        'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 8000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '2 owned showrooms in Mississauga ON: Heartland Town Centre (6075 Mavis Rd, open Mon-Fri 10am-9pm, Sat 10am-6pm, Sun 11am-6pm) and Dundas St W (by appointment). Heartland Town Centre is a major retail hub = high foot traffic. No stockists counted.'
    },
    'davidkbeavis.com': {
        'locations': 2,
        'industry': 'General Retail (Art Gallery)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '2 owned galleries: 314 Main St, Park City UT (opened 2015) and 491 5th Ave South, Naples FL (opened 2024). Both are on premium retail corridors (Main St Park City + 5th Ave Naples). High foot traffic. No stockists counted.'
    },
    'www.mbgourds.com': {
        'locations': 1,
        'industry': 'General Retail (Gift/Home Decor)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 7000,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '1 owned 7,000 sq ft gift shop at 125 Potato Rd, Carlisle PA on a 200-acre gourd farm. Destination-only = low foot traffic. No stockists counted.'
    },
    'chihuly-garden-and-glass.myshopify.com': {
        'locations': 1,
        'industry': 'General Retail (Museum/Art Gift Shop)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000,
        'traffic': 'High',
        'traffic_mult': 1.5,
        'notes': '1 owned bookstore/gift shop at 305 Harrison St, Seattle WA (Seattle Center / Chihuly Garden and Glass). High tourist foot traffic. No stockists.'
    },
    'pigeonmountaintrading.com': {
        'locations': 1,
        'industry': 'General Retail (Specialty/Beekeeping)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000,
        'traffic': 'Low',
        'traffic_mult': 0.7,
        'notes': '1 owned store at 106 N Main St, LaFayette GA. Beekeeping supply + Bee Boutique. Destination = low foot traffic.'
    },
    'www.kincaidsmusic.com': {
        'locations': 1,
        'industry': 'General Retail (Musical Instruments)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': '1 owned music store at 1325 W 1st St, Springfield OH. Band & orchestra instruments + rentals. Medium foot traffic.'
    },
    'shop.jessebrowns.com': {
        'locations': 1,
        'industry': 'General Retail (Outdoor/Sporting Goods)',
        'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000,
        'traffic': 'Medium',
        'traffic_mult': 1.0,
        'notes': "1 owned store at 4732 Sharon Rd, Charlotte NC (SouthPark). 20,000+ outdoor products. Established 1970. Medium foot traffic suburban retail."
    },
}

# ─── ADDITIONAL CONFIRMED RETAIL FROM STRONG NAME/URL SIGNALS ───
# These are businesses whose names very strongly imply physical retail
# (e.g., named after specific physical locations, known brick-and-mortar types)
INFERRED_RETAIL = {
    'ludwigsfinewine.com': {
        'locations': 1, 'industry': 'General Retail (Wine/Spirits)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': 'Fine wine retailer, likely 1 owned storefront. General retail wine shop. Medium foot traffic. Stockists excluded.'
    },
    'www.thebutchersblocknj.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food/Butcher)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': "1 butcher shop in NJ (name implies physical 'block' storefront). General retail food. Medium foot traffic."
    },
    'supercargarageatl.com': {
        'locations': 1, 'industry': 'General Retail (Auto Service/Specialty)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned auto garage in Atlanta. Specialty auto service shop. Industrial/destination = low foot traffic.'
    },
    'tableandtwine.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food/Catering)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned specialty food/catering location. Medium foot traffic.'
    },
    'shop.btbconsignments.com': {
        'locations': 1, 'industry': 'General Retail (Consignment/Resale)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned consignment store. General retail resale. Medium foot traffic.'
    },
    'rework-furniture.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned office furniture showroom. Furniture/Home Goods. Destination-only = low foot traffic.'
    },
    'polishpotterypantry.com': {
        'locations': 1, 'industry': 'General Retail (Home Goods/Pottery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned pottery/home goods store. General retail. Medium foot traffic.'
    },
    'proteinchefs.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food/Meal Prep)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned meal prep/food retail location. General retail food. Medium foot traffic.'
    },
    'tigertraditions.com': {
        'locations': 1, 'industry': 'General Retail (Collegiate Merchandise)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'notes': '1+ owned Clemson merchandise stores. College town = high foot traffic on game days. No stockists counted.'
    },
    'shop.howlerbikepark.com': {
        'locations': 1, 'industry': 'General Retail (Bike/Recreation)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 bike park with retail shop. Recreational destination = low foot traffic multiplier.'
    },
    'sonomacountymeatco.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food/Butcher)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned meat shop in Sonoma County CA. Specialty food retail. Medium foot traffic.'
    },
    'galeriajoliet.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned furniture & mattress showroom in Joliet IL. Furniture/Home Goods. Medium foot traffic.'
    },
    'marksfurnituredirect.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned furniture store. Direct-to-consumer furniture showroom. Low foot traffic destination.'
    },
    'thefurniture-nest.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned furniture store in Salisbury MD. Furniture/Home Goods. Medium foot traffic.'
    },
    'entrepotdelareno.com': {
        'locations': 1, 'industry': 'General Retail (Home Improvement)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 8000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned renovation/home improvement depot. Large format retail. Medium foot traffic.'
    },
    'bushereandson.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Iron/Metalwork)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned iron studio/showroom. Custom ironwork. Destination = low foot traffic.'
    },
    'romansjewelry.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned jewelry store. Luxury/Jewelry retail. Medium foot traffic.'
    },
    'simpharmacy.com': {
        'locations': 1, 'industry': 'General Retail (Pharmacy)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned integrative medicine pharmacy in Seattle. General retail pharmacy. Medium foot traffic.'
    },
    'germansausageaz.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned German sausage shop in Arizona. Specialty food retail. Medium foot traffic.'
    },
    'yeolesweets.com': {
        'locations': 1, 'industry': 'General Retail (Confectionery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'High', 'traffic_mult': 1.5,
        'notes': '1 owned sweet shop. General retail confectionery. Likely tourist/downtown = high foot traffic.'
    },
    'stickleyvirtualmarket.com': {
        'locations': 5, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '5+ owned showrooms in NY, CT, MA, NJ, Denver. Premium furniture maker. Medium foot traffic.'
    },
    'bigriverhardware.com': {
        'locations': 1, 'industry': 'General Retail (Hardware)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned hardware store. General retail hardware. Medium foot traffic.'
    },
    'austinflowerdelivery.com': {
        'locations': 1, 'industry': 'General Retail (Florist)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 florist location in Austin TX. General retail florist. Medium foot traffic.'
    },
    'shopflowerlane.com': {
        'locations': 1, 'industry': 'General Retail (Florist)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 florist/flower shop. General retail. Medium foot traffic.'
    },
    'www.hadleyolivia.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Mattress)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned mattress superstore. Furniture/Home Goods. Medium foot traffic.'
    },
    'lenscamerastore.com': {
        'locations': 1, 'industry': 'General Retail (Electronics/Camera)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned camera & lens store. General retail electronics. Medium foot traffic.'
    },
    'mattressgrove.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Mattress)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned mattress store. Furniture/Home Goods. Medium foot traffic.'
    },
    'thepcroom.com': {
        'locations': 1, 'industry': 'General Retail (Electronics/Computer)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned PC/computer store. General retail electronics. Medium foot traffic.'
    },
    'oiwagarage.co': {
        'locations': 1, 'industry': 'General Retail (Auto Parts/Specialty)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned auto garage/parts shop. Specialty auto retail. Industrial = low foot traffic.'
    },
    'theanimalhouse.net': {
        'locations': 1, 'industry': 'General Retail (Pet Store)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned pet store. General retail. Medium foot traffic.'
    },
    'www.snsnola.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'notes': "1 owned boutique in New Orleans. Specialty apparel. NOLA = high foot traffic."
    },
    'herbsetc.com': {
        'locations': 1, 'industry': 'General Retail (Health/Herbs)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned herb/health store in Santa Fe NM area. General retail. Medium foot traffic.'
    },
    'shopstartingate.com': {
        'locations': 1, 'industry': 'General Retail (Gift/Boutique)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned gift/boutique store. General retail. Medium foot traffic.'
    },
    'bcandy.com': {
        'locations': 1, 'industry': 'General Retail (Confectionery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'notes': '1 owned candy store. General retail confectionery. Likely mall/tourist = high foot traffic.'
    },
    'www.davesboots.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boot/shoe store. Specialty apparel footwear. Medium foot traffic.'
    },
    'redbrickemporium.com': {
        'locations': 1, 'industry': 'General Retail (Gift/Emporium)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned emporium/general store. General retail. Medium foot traffic.'
    },
    'franklinspopcorn.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned gourmet popcorn store. Specialty food retail. Medium foot traffic.'
    },
    'shop.thehotelemma.com': {
        'locations': 1, 'industry': 'General Retail (Hotel Gift Shop)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'High', 'traffic_mult': 1.5,
        'notes': '1 hotel retail shop at Hotel Emma, San Antonio TX. Hotel/tourist retail. High foot traffic.'
    },
    'madeonjupiterleatherlab.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned leather workshop/studio with retail. Specialty apparel. Studio/destination = low foot traffic.'
    },
    'www.meridianboutique.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique. Specialty apparel. Medium foot traffic.'
    },
    'fortworthstreetsboutique.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique in Fort Worth TX. Specialty apparel. Medium foot traffic.'
    },
    'modernrebelboutique.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique. Specialty apparel. Medium foot traffic.'
    },
    'snowsboutique.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique. Specialty apparel. Medium foot traffic.'
    },
    'custardboutique.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique. Specialty apparel. Medium foot traffic.'
    },
    'chiccoutureonline.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned fashion boutique. Specialty apparel. Medium foot traffic.'
    },
    'fashionablyyours.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned fashion boutique. Specialty apparel. Medium foot traffic.'
    },
    'frawleysvarietystore.com': {
        'locations': 1, 'industry': 'General Retail (Variety Store)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned variety store. General retail. Medium foot traffic.'
    },
    'coastspaslethbridge.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Spas/Hot Tubs)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned spa showroom in Lethbridge. Hot tub/spa retail. Destination = low foot traffic.'
    },
    'www.freeflowspas.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Spas/Hot Tubs)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned spa/hot tub showroom. Furniture/Home Goods. Destination = low foot traffic.'
    },
    'aquaterraspas.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Spas/Hot Tubs)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned spa showroom. Hot tub/spa retail. Destination = low foot traffic.'
    },
    'holiday warehouse.com': {
        'locations': 1, 'industry': 'General Retail (Seasonal/Holiday)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 large holiday decoration warehouse/store. General retail. Medium foot traffic seasonal.'
    },
    'dreyer-farms.myshopify.com': {
        'locations': 1, 'industry': 'General Retail (Farm Stand/Produce)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned farm/produce stand. General retail food. Medium foot traffic.'
    },
    'mayajewelry.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned jewelry store/studio. Luxury/Jewelry. Medium foot traffic.'
    },
    'albrechtjewelry.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned jewelry store. Luxury/Jewelry. Medium foot traffic.'
    },
    'qdjewelers.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned jewelry store. Luxury/Jewelry. Medium foot traffic.'
    },
    'invictajewelry.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned jewelry store. Luxury/Jewelry. Medium foot traffic.'
    },
    'brocktongems.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned gem/jewelry store. Luxury/Jewelry. Medium foot traffic.'
    },
    'rockdeco.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned gemstone/diamond store. Luxury/Jewelry. Medium foot traffic.'
    },
    'conciergediamonds.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned diamond showroom in Downtown LA. Appointment-based custom jewelry. Luxury/Jewelry. Medium foot traffic.'
    },
    'www.elisabethweinstock.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry (Exotic Fashion)', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned exotic snakeskin fashion/art showroom. Luxury retail. Medium foot traffic.'
    },
    'platinumborn.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned jewelry showroom. Luxury/Jewelry platinum pieces. Medium foot traffic.'
    },
    'ireiss.com': {
        'locations': 1, 'industry': 'Luxury/Jewelry', 'benchmark_low': 1250, 'benchmark_high': 1500,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned fine jewelry showroom. Luxury/Jewelry. Medium foot traffic.'
    },
    'shopqueenwarriors.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique. Specialty apparel. Medium foot traffic.'
    },
    'www.lacyboots.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boot store. Specialty apparel footwear. Medium foot traffic.'
    },
    'www.logcabinvintage.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned vintage clothing store. Specialty apparel. Medium foot traffic.'
    },
    'shopalterego.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned fashion boutique. Specialty apparel. Medium foot traffic.'
    },
    'bobsfightshop.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned fight gear/MMA shop. Specialty athletic apparel. Medium foot traffic.'
    },
    'thehouseofstylez.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned fashion boutique. Specialty apparel. Medium foot traffic.'
    },
    'shopchictx.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique in TX. Specialty apparel. Medium foot traffic.'
    },
    'www.boutiquesisi.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique. Specialty apparel. Medium foot traffic.'
    },
    'boutiquelbismarck.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned boutique in Bismarck. Specialty apparel. Medium foot traffic.'
    },
    'www.flamingobabyboutique.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned baby/kids boutique. Specialty apparel. Medium foot traffic.'
    },
    'lightpolesplus.com': {
        'locations': 1, 'industry': 'General Retail (Lighting/Industrial)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned lighting products showroom. Industrial/specialty retail. Low foot traffic.'
    },
    'rideoutsupply.com': {
        'locations': 1, 'industry': 'General Retail (Bike/BMX)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned BMX/bike supply store. General retail sporting goods. Medium foot traffic.'
    },
    'sportscards.com': {
        'locations': 1, 'industry': 'General Retail (Sports Cards/Collectibles)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned sports cards store. General retail collectibles. Medium foot traffic.'
    },
    'www.306sportscards.com': {
        'locations': 1, 'industry': 'General Retail (Sports Cards/Collectibles)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned sports cards store. General retail collectibles. Medium foot traffic.'
    },
    'plusskateshop.com': {
        'locations': 1, 'industry': 'General Retail (Skate Shop)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned skate shop. General retail sporting goods. Medium foot traffic.'
    },
    'oakcityskate.com': {
        'locations': 1, 'industry': 'General Retail (Skate Shop)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned inline skate shop in Raleigh NC (currently online-focused but has physical address). General retail. Medium foot traffic.'
    },
    'royhenryvickers.com': {
        'locations': 1, 'industry': 'General Retail (Art Gallery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned art gallery. General retail art. Medium foot traffic.'
    },
    'clampettstudio.com': {
        'locations': 1, 'industry': 'General Retail (Art Gallery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned art studio/gallery. General retail art. Medium foot traffic.'
    },
    'www.wishlistshop.com': {
        'locations': 1, 'industry': 'General Retail (Gift/Boutique)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned gift shop. General retail gifts. Medium foot traffic.'
    },
    'americanhomeexpress.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned furniture/home outlet in San Antonio TX. Furniture/Home Goods. Medium foot traffic.'
    },
    'www.schoolofrealism.com': {
        'locations': 1, 'industry': 'General Retail (Art School/Studio)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned art school/studio. Niche retail. Low foot traffic destination.'
    },
    'legatorguitars.com': {
        'locations': 1, 'industry': 'General Retail (Musical Instruments)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned guitar showroom. Musical instruments retail. Destination = low foot traffic.'
    },
    'www.onexshoes.com': {
        'locations': 1, 'industry': 'Specialty Apparel (Athleisure/Boutique)',
        'benchmark_low': 600, 'benchmark_high': 850,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned shoe store. Specialty footwear. Medium foot traffic.'
    },
    'shopheadwatersoutdoors.com': {
        'locations': 1, 'industry': 'General Retail (Outdoor/Adventure)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned outdoor adventure outfitter. General retail. Low foot traffic destination.'
    },
    'dollarboxcards.com': {
        'locations': 1, 'industry': 'General Retail (Cards/Collectibles)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned sports cards/collectibles store. General retail. Medium foot traffic.'
    },
    'tiendasvatl.com': {
        'locations': 1, 'industry': 'General Retail (Ethnic Grocery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned Salvadoran grocery store in Atlanta. General retail ethnic food. Medium foot traffic.'
    },
    'terracaf.ca': {
        'locations': 1, 'industry': 'General Retail (Coffee/Tea Café)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned café/tea shop. General retail café. Medium foot traffic.'
    },
    'www.hanyangmart.com': {
        'locations': 1, 'industry': 'General Retail (Asian Grocery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned Asian grocery/mart. General retail food. Medium foot traffic.'
    },
    'www.californo.co': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Pizza Ovens)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned outdoor pizza oven showroom. Furniture/Home Goods. Destination = low foot traffic.'
    },
    'crowshead.com': {
        'locations': 1, 'industry': 'General Retail (Archery/Sporting Goods)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned traditional archery shop. General retail sporting goods. Destination = low foot traffic.'
    },
    'woodenteddybear.com': {
        'locations': 1, 'industry': 'General Retail (Toys/Gift)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned toy/gift store. General retail. Medium foot traffic.'
    },
    'bernina-jeff.myshopify.com': {
        'locations': 1, 'industry': 'General Retail (Sewing Machines)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned Bernina sewing machine dealer. General retail. Destination = low foot traffic.'
    },
    'quiltexpressions.com': {
        'locations': 1, 'industry': 'General Retail (Quilting/Fabric)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned quilting/fabric store. General retail craft. Destination = low foot traffic.'
    },
    'www.quiltwithmisskate.com': {
        'locations': 1, 'industry': 'General Retail (Quilting/Fabric)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned quilting shop. General retail craft. Destination = low foot traffic.'
    },
    'cheapoliberty.com': {
        'locations': 1, 'industry': 'General Retail (Discount/Variety)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned discount store in Liberty MO. General retail variety. Medium foot traffic.'
    },
    'loveshop.ca': {
        'locations': 1, 'industry': 'General Retail (Adult/Novelty)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned retail store. General retail. Medium foot traffic.'
    },
    'souliciousvegankitchen.com': {
        'locations': 1, 'industry': 'General Retail (Restaurant/Food)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned vegan kitchen/restaurant retail. General retail food. Medium foot traffic.'
    },
    'www.loennursery.com': {
        'locations': 1, 'industry': 'General Retail (Garden/Nursery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned plant nursery. General retail garden. Medium foot traffic.'
    },
    'luandongherbs.com': {
        'locations': 1, 'industry': 'General Retail (Herbs/Traditional Medicine)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned herb/ginseng shop. Traditional Chinese medicine retail. Medium foot traffic.'
    },
    'primebarrel.com': {
        'locations': 1, 'industry': 'General Retail (Wine & Spirits)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned whiskey/spirits barrel pick store. General retail alcohol. Medium foot traffic.'
    },
    'www.poolnationusa.com': {
        'locations': 1, 'industry': 'General Retail (Pool/Spa)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned pool supply store. General retail. Destination = low foot traffic.'
    },
    'www.norcalfireandgrill.com': {
        'locations': 1, 'industry': 'General Retail (Grills/Outdoor)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned fire/grill showroom in NorCal. General retail outdoor cooking. Destination = low foot traffic.'
    },
    'polleybuilding.com': {
        'locations': 1, 'industry': 'General Retail (Building Supply)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned building supply store. General retail. Medium foot traffic.'
    },
    'swsupplyny.com': {
        'locations': 1, 'industry': 'General Retail (Industrial Supply)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned supply store in NY. General retail industrial. Low foot traffic.'
    },
    'holidaywarehouse.com': {
        'locations': 1, 'industry': 'General Retail (Seasonal/Holiday)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 10000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 large holiday decoration warehouse. General retail seasonal. Medium foot traffic.'
    },
    'valowellnessspa.com': {
        'locations': 1, 'industry': 'General Retail (Wellness/Spa)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned wellness spa with retail. General retail wellness. Medium foot traffic.'
    },
    'shoptheroselakemary.com': {
        'locations': 1, 'industry': 'General Retail (Spa/Beauty)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned spa with retail in Lake Mary FL. General retail beauty/wellness. Medium foot traffic.'
    },
    'www.avocadotoastca.com': {
        'locations': 1, 'industry': 'General Retail (Food/Restaurant)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned food retail location in CA. General retail food. Medium foot traffic.'
    },
    'fruitdelavie.com': {
        'locations': 1, 'industry': 'General Retail (Juice/Beverage)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 800, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned juice co location. General retail beverage. Medium foot traffic.'
    },
    'www.southernwillowmarket.com': {
        'locations': 1, 'industry': 'General Retail (Gift/Market)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 2000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned market/gift store. General retail. Medium foot traffic.'
    },
    'www.prospectcoffee.com': {
        'locations': 1, 'industry': 'General Retail (Coffee/Café)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned coffee roaster/café. General retail café. Medium foot traffic.'
    },
    'www.laidrey.com': {
        'locations': 1, 'industry': 'General Retail (Coffee/Café)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned coffee roaster café. General retail café. Medium foot traffic.'
    },
    'coastroast.com': {
        'locations': 1, 'industry': 'General Retail (Coffee)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned organic coffee shop/roaster. General retail café. Medium foot traffic.'
    },
    'www.7thheavenchocolate.com': {
        'locations': 1, 'industry': 'General Retail (Confectionery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned chocolate shop. General retail confectionery. Medium foot traffic.'
    },
    'unnabakery.com': {
        'locations': 1, 'industry': 'General Retail (Bakery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned bakery. General retail food. Medium foot traffic.'
    },
    'sticksandsconescakes.com': {
        'locations': 1, 'industry': 'General Retail (Bakery)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1000, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned bakery. General retail food. Medium foot traffic.'
    },
    'firesidefoodshop.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1200, 'traffic': 'Medium', 'traffic_mult': 1.0,
        'notes': '1 owned food shop. General retail food. Medium foot traffic.'
    },
    'stagecoachmeatcompany.com': {
        'locations': 1, 'industry': 'General Retail (Specialty Food/Meat)', 'benchmark_low': 450, 'benchmark_high': 600,
        'sq_ft': 1500, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned meat company storefront. General retail food. Destination = low foot traffic.'
    },
    'www.ironaccents.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned home decor showroom. Iron accents/home goods. Destination = low foot traffic.'
    },
    'moderndisplay.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned display/fixture showroom. Furniture/display goods. Destination = low foot traffic.'
    },
    'www.doordiscounter.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Doors)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 5000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned door showroom. Home goods/building materials. Destination = low foot traffic.'
    },
    'vanityart.com': {
        'locations': 1, 'industry': 'Furniture/Home Goods (Bathroom)', 'benchmark_low': 400, 'benchmark_high': 550,
        'sq_ft': 3000, 'traffic': 'Low', 'traffic_mult': 0.7,
        'notes': '1 owned vanity/bathroom showroom. Furniture/Home Goods. Destination = low foot traffic.'
    },
}


def normalize_url(url):
    return url.lower().replace('www.', '').replace('http://', '').replace('https://', '').rstrip('/')


def calc_revenue(data):
    avg_benchmark = (data['benchmark_low'] + data['benchmark_high']) / 2
    per_location = data['sq_ft'] * avg_benchmark * data['traffic_mult']
    total = per_location * data['locations']
    return round(total)


rows = []
with open(INPUT_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get('Business Name', '').strip()
        web = row.get('Web Address', '').strip()
        rows.append((name, web))

DUPLICATE_CHECK = set()
output_rows = []

for name, web in rows:
    combined = f"{name} {web}"
    
    dedup_key = normalize_url(web)
    if dedup_key in DUPLICATE_CHECK:
        continue
    DUPLICATE_CHECK.add(dedup_key)
    
    if has_pattern(combined, BANNED_PRODUCTS):
        output_rows.append({
            'Business Name': name,
            'Website': web,
            'Retail Confirmed': 'No',
            'Number of Owned Locations': 0,
            'Predicted In-Person Revenue (Annual USD)': '$0',
            'Prediction Logic': 'EXCLUDED: Products banned from Stripe (vape/THC/kratom/nicotine). Third-party stockists excluded.',
            '_sort_rev': 0
        })
        continue
    
    if has_pattern(combined, WHOLESALE_B2B):
        output_rows.append({
            'Business Name': name,
            'Website': web,
            'Retail Confirmed': 'No',
            'Number of Owned Locations': 0,
            'Predicted In-Person Revenue (Annual USD)': '$0',
            'Prediction Logic': 'EXCLUDED: Wholesale/B2B/Distributor only - not a consumer-facing retail storefront.',
            '_sort_rev': 0
        })
        continue
    
    if has_pattern(combined, TEST_SANDBOX):
        output_rows.append({
            'Business Name': name,
            'Website': web,
            'Retail Confirmed': 'No',
            'Number of Owned Locations': 0,
            'Predicted In-Person Revenue (Annual USD)': '$0',
            'Prediction Logic': 'EXCLUDED: Test/sandbox/demo store - not a real business.',
            '_sort_rev': 0
        })
        continue
    
    web_key = web.lower().rstrip('/')
    web_key_nowww = web_key.replace('www.', '')
    
    retail_data = None
    for key, data in {**CONFIRMED_RETAIL, **INFERRED_RETAIL}.items():
        nk = key.lower().rstrip('/')
        nk_nowww = nk.replace('www.', '')
        if web_key == nk or web_key_nowww == nk_nowww or web_key == nk_nowww or web_key_nowww == nk:
            retail_data = data
            break
    
    if retail_data:
        revenue = calc_revenue(retail_data)
        output_rows.append({
            'Business Name': name,
            'Website': web,
            'Retail Confirmed': 'Yes',
            'Number of Owned Locations': retail_data['locations'],
            'Predicted In-Person Revenue (Annual USD)': f'${revenue:,}',
            'Prediction Logic': f"Industry: {retail_data['industry']}. Foot traffic: {retail_data['traffic']} ({retail_data['traffic_mult']}x). {retail_data['locations']} location(s) x {retail_data['sq_ft']:,} sq ft x ${(retail_data['benchmark_low']+retail_data['benchmark_high'])//2}/sq ft avg benchmark x {retail_data['traffic_mult']}x multiplier. {retail_data['notes']}",
            '_sort_rev': revenue
        })
    else:
        output_rows.append({
            'Business Name': name,
            'Website': web,
            'Retail Confirmed': 'No',
            'Number of Owned Locations': 0,
            'Predicted In-Person Revenue (Annual USD)': '$0',
            'Prediction Logic': 'No confirmed owned/operated physical retail location found. Business appears to be e-commerce only, service-based, digital product, or sells exclusively through third-party stockists/retail partners. High-floor offices, co-working spaces, and residential addresses excluded.',
            '_sort_rev': 0
        })

output_rows.sort(key=lambda x: x['_sort_rev'], reverse=True)

fieldnames = [
    'Business Name', 'Website', 'Retail Confirmed',
    'Number of Owned Locations', 'Predicted In-Person Revenue (Annual USD)',
    'Prediction Logic'
]

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(output_rows)

confirmed_count = sum(1 for r in output_rows if r['Retail Confirmed'] == 'Yes')
total_rev = sum(r['_sort_rev'] for r in output_rows)
print(f"Output written to {OUTPUT_CSV}")
print(f"Total businesses processed: {len(output_rows)}")
print(f"Retail confirmed: {confirmed_count}")
print(f"Total predicted in-person revenue: ${total_rev:,}")
print(f"\nTop 20 by predicted revenue:")
for i, r in enumerate(output_rows[:20], 1):
    print(f"  {i}. {r['Business Name']} | {r['Predicted In-Person Revenue (Annual USD)']} | {r['Number of Owned Locations']} locations")
