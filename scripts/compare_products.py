import urllib.request
import os
import re

# Fetch live
url = "https://www.todoparteshorizonte.com/products.js"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        live_content = response.read().decode('utf-8', errors='replace')
except Exception as e:
    live_content = ""
    print(f"Error fetching live: {e}")

# Read local
local_path = r"web\products.js"
if os.path.exists(local_path):
    with open(local_path, "r", encoding="utf-8") as f:
        local_content = f.read()
else:
    local_content = ""

print(f"Live size: {len(live_content)} chars")
print(f"Local size: {len(local_content)} chars")

# Find all product IDs in local using regex
local_ids = set(re.findall(r'"id":\s*"([^"]+)"', local_content))
live_ids = set(re.findall(r'"id":\s*"([^"]+)"', live_content))

print(f"Local has {len(local_ids)} product IDs")
print(f"Live has {len(live_ids)} product IDs")

only_local = local_ids - live_ids
print(f"IDs only in local ({len(only_local)}):")
for i, uid in enumerate(list(only_local)[:10]):
    # Find the description for this id in local
    match = re.search(r'"id":\s*"' + uid + r'".*?"description":\s*"([^"]+)"', local_content, re.DOTALL)
    desc = match.group(1) if match else "Unknown"
    print(f"  {uid}: {desc}")

only_live = live_ids - local_ids
print(f"IDs only in live ({len(only_live)}):")
for i, uid in enumerate(list(only_live)[:10]):
    match = re.search(r'"id":\s*"' + uid + r'".*?"description":\s*"([^"]+)"', live_content, re.DOTALL)
    desc = match.group(1) if match else "Unknown"
    print(f"  {uid}: {desc}")
