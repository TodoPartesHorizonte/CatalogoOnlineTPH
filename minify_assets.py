import re
import os

file_path = r'c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace png/jpg with webp except logo for favicons
content = re.sub(r'logo\.png', 'logo.webp', content)
content = re.sub(r'caribe_logo\.png', 'caribe_logo.webp', content)
content = re.sub(r'luv_logo\.png', 'luv_logo.webp', content)
content = re.sub(r'dmax_logo\.png', 'dmax_logo.webp', content)
content = re.sub(r'rodeo_logo\.png', 'rodeo_logo.webp', content)
content = re.sub(r'trooper_logo\.png', 'trooper_logo.webp', content)
content = re.sub(r'header_bg\.jpg', 'header_bg.webp', content)

# Restore favicon/meta tags to png
content = content.replace('href="./assets/logo.webp" type="image/png"', 'href="./assets/logo.png" type="image/png"')
content = content.replace('"https://todoparteshorizonte.github.io/CatalogoOnlineTPH/assets/logo.webp"', '"https://todoparteshorizonte.github.io/CatalogoOnlineTPH/assets/logo.png"')

# Extract CSS
css_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
if css_match:
    css = css_match.group(1)
    # Simple minify
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL) # remove comments
    css = re.sub(r'\s+', ' ', css) # replace whitespace
    css = css.replace('{ ', '{').replace(' }', '}').replace(': ', ':').replace('; ', ';').replace(', ', ',')
    with open(r'c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web\style.min.css', 'w', encoding='utf-8') as f:
        f.write(css.strip())
    # Note: Critical CSS inlining vs Deferred CSS.
    # The performance skill says:
    # <style>/* Above-fold styles */</style>
    # <link rel="preload" href="/styles.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
    # Since extracting all of it might cause FOUC (Flash of Unstyled Content), we can preload it or just use a standard blocking link if the file is very small.
    # We will use the preload pattern with noscript.
    content = content.replace(css_match.group(0), '<link rel="preload" href="./style.min.css" as="style" onload="this.onload=null;this.rel=\'stylesheet\'">\n    <noscript><link rel="stylesheet" href="./style.min.css"></noscript>')

# Extract JS
js_match = re.search(r'<!-- JAVASCRIPT DE CONTROL -->\s*<script>(.*?)</script>', content, re.DOTALL)
if js_match:
    js = js_match.group(1)
    # Write to app.js
    with open(r'c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web\app.min.js', 'w', encoding='utf-8') as f:
        f.write(js.strip())
    content = content.replace(js_match.group(0), '<!-- JAVASCRIPT DE CONTROL -->\n    <script defer src="./app.min.js"></script>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
