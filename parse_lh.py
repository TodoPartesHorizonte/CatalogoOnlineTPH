import json

with open('lighthouse.json', encoding='utf-8') as f:
    d = json.load(f)

print(f"Performance Score: {d['categories']['performance']['score']*100}")
print(f"FCP: {d['audits']['first-contentful-paint']['displayValue']}")
print(f"LCP: {d['audits']['largest-contentful-paint']['displayValue']}")
print(f"TBT: {d['audits']['total-blocking-time']['displayValue']}")
print(f"CLS: {d['audits']['cumulative-layout-shift']['displayValue']}")
print(f"Speed Index: {d['audits']['speed-index']['displayValue']}")
