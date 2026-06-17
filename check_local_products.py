import os

p = r"web\products.js"
if os.path.exists(p):
    print(f"Local size: {os.path.getsize(p)} bytes")
else:
    print("Local products.js does not exist")
