import re
file_path = r'c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web\app.min.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the ReferenceError by properly replacing the forEach
old_loop = r'filteredProducts\.forEach\(product => \{'
new_loop = 'filteredProducts.forEach((product, index) => {\n                let imgPriority = index < 4 ? \'fetchpriority="high"\' : \'loading="lazy"\';'
content = re.sub(old_loop, new_loop, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed loop!')
