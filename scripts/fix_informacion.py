import codecs
import re

with codecs.open('web/informacion.html', 'r', 'utf-8') as f:
    lines = f.readlines()

# find <style> and </style>
start = -1
end = -1
for i, line in enumerate(lines):
    if '<style>' in line and start == -1:
        start = i
    if '</style>' in line:
        end = i

if start != -1 and end != -1:
    css_lines = lines[start+1:end]
    with codecs.open('web/informacion.css', 'w', 'utf-8') as f:
        f.writelines(css_lines)
    
    # Extract lines
    new_lines = []
    
    i = 0
    while i < len(lines):
        if i == start:
            new_lines.append('    <link rel="stylesheet" href="./informacion.css">\n')
            i = end + 1
            continue
            
        line = lines[i]
        
        # Add skip link
        if '<body>' in line:
            new_lines.append(line)
            new_lines.append('    <a href="#main-content" class="skip-link">Saltar al contenido principal</a>\n')
            i += 1
            continue
            
        # Add main-content id
        if '<div class="container">' in line:
            new_lines.append(line.replace('<div class="container">', '<div class="container" id="main-content">'))
            i += 1
            continue
            
        new_lines.append(line)
        i += 1
        
    with codecs.open('web/informacion.html', 'w', 'utf-8') as f:
        f.writelines(new_lines)
    print("Done fixes on informacion.html")
else:
    print("Tags not found")
