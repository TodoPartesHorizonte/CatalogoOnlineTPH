import codecs

with codecs.open('web/informacion.html', 'r', 'utf-8') as f:
    lines = f.readlines()

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
    
    new_lines = lines[:start] + ['    <link rel="stylesheet" href="./informacion.css">\n'] + lines[end+1:]
    with codecs.open('web/informacion.html', 'w', 'utf-8') as f:
        f.writelines(new_lines)
    print("Done")
else:
    print("Tags not found")
