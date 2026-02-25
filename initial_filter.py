import csv
import re

WHOLESALE_PATTERNS = [
    r'\bwholesale\b', r'\bb2b\b', r'\bdistribut', r'\bpro\s+(store|shop)\b',
    r'\bdealer\b', r'\btrade\b', r'wholesale\.', r'b2b\.', r'distributor\.',
    r'retail\.littleunicorn', r'canadawholesale', r'fair-indigo-wholesale',
]

TEST_SANDBOX_PATTERNS = [
    r'\btest\b', r'\bsandbox\b', r'\bdemo\b', r'test\.myshopify',
    r'sandbox', r'soundtoys-test',
]

DIGITAL_ONLY_PATTERNS = [
    r'\bdigital\b.*\b(download|product)\b', r'sheet-music-lib',
    r'\bpodcast\b', r'\bonline\s+school\b', r'\bcourse', r'\bebook\b',
]

BANNED_PRODUCT_PATTERNS = [
    r'\bvape\b', r'\bvaping\b', r'\bcannabis\b', r'\bthc\b', r'\bhhc\b',
    r'\bkratom\b', r'\bnicotine\b', r'\bsmokin\b', r'\bdabbing\b',
    r'\bfoger\s*vape', r'\bbaked\s*hhc\b', r'\bcryo\s*kratom\b',
]

DUPLICATE_CHECK = set()

def has_pattern(text, patterns):
    text_lower = text.lower()
    for p in patterns:
        if re.search(p, text_lower):
            return True
    return False

RETAIL_POSITIVE_PATTERNS = [
    r'\bboutique\b', r'\bshowroom\b', r'\bstore\b', r'\bshop\b',
    r'\bfarm\b', r'\bmarket\b', r'\bgallery\b', r'\bjewel', r'\bspa\b',
    r'\bpharmacy\b', r'\bcafe\b', r'\bcoffee\b', r'\bbakery\b',
    r'\bfurniture\b', r'\bhardware\b', r'\bflorist\b', r'\blocker\b',
    r'\bgeneral store\b', r'\bconsignment\b', r'\bempori', r'\bsweet',
    r'\bchocolat', r'\bcandy\b', r'\bice cream\b', r'\bpretzel',
    r'\bwine\b', r'\bspirit', r'\bbar\b', r'\bgrill\b', r'\brestaurant\b',
    r'\btavern\b', r'\bpub\b', r'\btrade\s*show\b', r'\boutfit',
    r'\bboots\b', r'\bshoes\b', r'\bskate\s*shop\b', r'\bbike\b',
    r'\bmusic\b.*\bstore\b', r'\binstrument', r'\bguitar', r'\brecord\b',
    r'\bbilliard', r'\bpool\b.*\bstore\b', r'\bbowling\b',
    r'\bmattress\b', r'\bnursery\b', r'\bgarden\b', r'\btile\b',
    r'\bfloor\b', r'\bpaint\b', r'\blumber\b', r'\bbuilding supply\b',
]

rows = []
with open('/home/ubuntu/.cursor/projects/workspace/uploads/potential_retail_-_Sheet1__1_.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get('Business Name', '').strip()
        web = row.get('Web Address', '').strip()
        rows.append((name, web))

excluded_wholesale = []
excluded_test = []
excluded_banned = []
excluded_duplicate = []
remaining = []

for name, web in rows:
    combined = f"{name} {web}"
    
    dedup_key = web.lower().replace('www.', '').replace('http://', '').replace('https://', '').rstrip('/')
    if dedup_key in DUPLICATE_CHECK:
        excluded_duplicate.append((name, web, "Duplicate URL"))
        continue
    DUPLICATE_CHECK.add(dedup_key)
    
    if has_pattern(combined, BANNED_PRODUCT_PATTERNS):
        excluded_banned.append((name, web, "Banned product (vape/THC/kratom/nicotine)"))
        continue
    
    if has_pattern(combined, WHOLESALE_PATTERNS):
        excluded_wholesale.append((name, web, "Wholesale/B2B/Distributor"))
        continue
    
    if has_pattern(combined, TEST_SANDBOX_PATTERNS):
        excluded_test.append((name, web, "Test/Sandbox/Demo store"))
        continue
    
    remaining.append((name, web))

print(f"Total entries: {len(rows)}")
print(f"Excluded - Duplicates: {len(excluded_duplicate)}")
print(f"Excluded - Banned products: {len(excluded_banned)}")
print(f"Excluded - Wholesale/B2B: {len(excluded_wholesale)}")
print(f"Excluded - Test/Sandbox: {len(excluded_test)}")
print(f"Remaining for analysis: {len(remaining)}")

print("\n=== BANNED ===")
for n, w, r in excluded_banned:
    print(f"  {n} | {w} | {r}")

print("\n=== WHOLESALE/B2B ===")
for n, w, r in excluded_wholesale:
    print(f"  {n} | {w} | {r}")

print("\n=== TEST/SANDBOX ===")
for n, w, r in excluded_test:
    print(f"  {n} | {w} | {r}")

print("\n=== DUPLICATES ===")
for n, w, r in excluded_duplicate:
    print(f"  {n} | {w} | {r}")

retail_likely = []
for name, web in remaining:
    combined = f"{name} {web}"
    if has_pattern(combined, RETAIL_POSITIVE_PATTERNS):
        retail_likely.append((name, web))

print(f"\n=== LIKELY RETAIL (pattern match): {len(retail_likely)} ===")
for n, w in retail_likely[:50]:
    print(f"  {n} | {w}")
if len(retail_likely) > 50:
    print(f"  ... and {len(retail_likely)-50} more")
