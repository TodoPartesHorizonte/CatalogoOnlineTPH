from playwright.sync_api import sync_playwright
import sys

def run_test():
    print("Iniciando pruebas E2E con Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navegando a http://localhost:8000...")
        page.goto('http://localhost:8000')
        page.wait_for_load_state('networkidle')
        
        # 1. Comprobar que carga el catálogo (estado inicial: carpetas)
        folders = page.locator('.category-card').count()
        print(f"OK: Cargadas {folders} carpetas de categorías.")
        
        if folders == 0:
            print("❌ Error: No se renderizaron las carpetas.")
            sys.exit(1)
            
        # 2. Probar la búsqueda
        print("Buscando el término 'filtro'...")
        page.fill('#searchInput', 'filtro')
        page.dispatch_event('#searchInput', 'change')
        page.wait_for_timeout(1000)
        
        products = page.locator('.product-card').count()
        print(f"OK: Mostrando {products} productos para la búsqueda 'filtro'.")
        
        # 3. Probar añadir al carrito
        if products > 0:
            print("Añadiendo el primer producto al carrito...")
            page.click('.card-btn-add:visible >> nth=0')
            page.wait_for_timeout(1000)
            
            badge_text = page.locator('#fabCartBadge').inner_text()
            print(f"OK: El carrito tiene {badge_text} items.")
            if badge_text != "1":
                print("❌ Error: El carrito no se actualizó correctamente.")
                sys.exit(1)
        
        print("¡Pruebas finalizadas con éxito!")
        browser.close()

if __name__ == "__main__":
    run_test()
