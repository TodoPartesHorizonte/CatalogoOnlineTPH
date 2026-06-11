import re
file_path = r'c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web\app.min.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make the replacement for LCP priority
old_loop = r'filteredProducts\.forEach\(\(product\) => \{'
new_loop = 'filteredProducts.forEach((product, index) => {\n                let imgPriority = index < 4 ? \'fetchpriority="high"\' : \'loading="lazy"\';'
content = re.sub(old_loop, new_loop, content)

old_img = r'<img src="\$\{product\.image_path\}" alt="\$\{product\.description\}" class="product-img img-lazy" loading="lazy" width="280" height="350" onload="this\.classList\.add\(\'img-loaded\'\)">'
new_img = '<img src="${product.image_path}" alt="${product.description}" class="product-img img-lazy" ${imgPriority} width="280" height="350" onload="this.classList.add(\'img-loaded\')">'
content = re.sub(old_img, new_img, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
