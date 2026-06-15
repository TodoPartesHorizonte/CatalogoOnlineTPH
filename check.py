import re
import json

with open('products.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Try to parse the JS as JSON (by stripping the variable declaration)
try:
    if content.startswith("const PRODUCTS_DATA="):
        json_str = content[len("const PRODUCTS_DATA="):].strip()
    elif content.startswith("const PRODUCTS_DATA ="):
        json_str = content[len("const PRODUCTS_DATA ="):].strip()
    else:
        json_str = content[content.find("{"):]
    
    if json_str.endswith(";"):
        json_str = json_str[:-1]
        
    data = json.loads(json_str)
    products = data.get("products", [])
    
    print(f"Total objects in list: {len(products)}")
    
    unique_ids = set([p["id"] for p in products])
    print(f"Unique IDs: {len(unique_ids)}")
    
    if len(products) != len(unique_ids):
        # find duplicates
        seen = set()
        dupes = []
        for p in products:
            if p["id"] in seen:
                dupes.append(p["id"])
            seen.add(p["id"])
        print(f"Duplicates: {dupes[:10]}")
except Exception as e:
    print(f"JSON Parsing failed: {e}")
    # fallback regex
    ids = re.findall(r'id:"([^"]+)"', content)
    if not ids:
        ids = re.findall(r'"id":"([^"]+)"', content)
    print(f"Total regex ids: {len(ids)}")
    print(f"Unique regex ids: {len(set(ids))}")
