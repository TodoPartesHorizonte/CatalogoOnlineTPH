css_to_add = """
/* Accesibilidad */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: #ff6a00;
    color: white;
    padding: 8px;
    z-index: 10000;
    transition: top 0.2s;
}
.skip-link:focus {
    top: 0;
}
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
"""

with open('web/style.min.css', 'a', encoding='utf-8') as f:
    f.write(css_to_add)

with open('web/informacion.css', 'a', encoding='utf-8') as f:
    f.write(css_to_add)

print("CSS added to both files.")
