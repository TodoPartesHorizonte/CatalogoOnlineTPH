import json
import os
import re
from generator import generate_unique_slug, read_catalog_js, write_catalog_js
from web.generate_seo_pages import generate_pages, generate_sitemap

def main():
    print("Reading catalog data...")
    data = read_catalog_js()
    if not data or 'products' not in data:
        print("Could not read products.js")
        return

    used_slugs = set()
    products = data['products']
    
    print(f"Processing {len(products)} products...")
    
    for prod in products:
        if prod.get("slug"):
            if prod["slug"] not in used_slugs:
                used_slugs.add(prod["slug"])
            else:
                prod["slug"] = None
                
    for prod in products:
        if not prod.get("slug"):
            prod["slug"] = generate_unique_slug(prod["description"], used_slugs)
            
    # Save back to products.js
    write_catalog_js(data)
    print("products.js updated with slugs.")
    
    # Regenerate SEO Pages
    print("Regenerating SEO pages...")
    generate_pages(data)
    generate_sitemap(data)
    
    print("Done!")

if __name__ == "__main__":
    main()
