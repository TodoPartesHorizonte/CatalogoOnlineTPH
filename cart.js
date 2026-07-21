// Cart manager for static product detail pages
(function() {
    const WHATSAPP_NUMBER = "584242116375";
    let cart = [];

    // Inject drawer HTML and styles if not present
    document.addEventListener("DOMContentLoaded", () => {
        injectCartUI();
        initCart();
        setupEventListeners();
    });

    function injectCartUI() {
        if (document.getElementById("cartDrawer")) return;

        // 1. Append Float Button (FAB)
        const fab = document.createElement("a");
        fab.href = "#";
        fab.className = "fab-whatsapp";
        fab.id = "fabWhatsapp";
        fab.setAttribute("aria-label", "Ver lista de cotización o enviar mensaje");
        fab.innerHTML = `
            <div class="fab-cart-badge" id="fabCartBadge">0</div>
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
            </svg>
        `;
        document.body.appendChild(fab);

        // 2. Append Drawer Container
        const drawer = document.createElement("div");
        drawer.className = "cart-drawer";
        drawer.id = "cartDrawer";
        drawer.innerHTML = `
            <div class="cart-header">
                <h3>Tu Lista de Pedido</h3>
                <button class="cart-clear-btn" id="cartClearBtn" style="display: none;">Vaciar</button>
                <button class="cart-close" id="cartCloseBtn" aria-label="Cerrar lista de pedido">&times;</button>
            </div>
            <div class="cart-body" id="cartItemsContainer"></div>
            <div class="cart-footer">
                <div class="cart-summary">
                    <span>Total de repuestos:</span>
                    <strong id="cartTotalItems">0</strong>
                </div>
                <button class="cart-submit-btn" id="cartSubmitBtn">
                    <svg viewBox="0 0 24 24" aria-hidden="true" style="width: 20px; height: 20px; fill: #fff; margin-right: 8px;">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                    </svg>
                    Enviar Pedido por WhatsApp
                </button>
            </div>
        `;
        document.body.appendChild(drawer);

        // 3. Append Overlay
        const overlay = document.createElement("div");
        overlay.className = "cart-overlay";
        overlay.id = "cartOverlay";
        document.body.appendChild(overlay);
    }

    function initCart() {
        try {
            const storedCart = sessionStorage.getItem('tph_cart');
            if (storedCart) {
                cart = JSON.parse(storedCart);
            }
        } catch (e) {
            console.error("Error al cargar el carrito de sessionStorage:", e);
            cart = [];
        }
        renderCart();
    }

    function saveCart() {
        try {
            sessionStorage.setItem('tph_cart', JSON.stringify(cart));
        } catch (e) {
            console.error("Error al guardar el carrito en sessionStorage:", e);
        }
    }

    function toggleCart(forceOpen) {
        const drawer = document.getElementById('cartDrawer');
        const overlay = document.getElementById('cartOverlay');
        if (!drawer || !overlay) return;

        const isOpen = typeof forceOpen === 'boolean' ? forceOpen : !drawer.classList.contains('active');

        if (isOpen) {
            drawer.classList.add('active');
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        } else {
            drawer.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    window.clearCart = function() {
        if (confirm("¿Estás seguro de que deseas vaciar toda tu lista de pedido?")) {
            cart = [];
            saveCart();
            renderCart();
            toggleCart(false);
        }
    };

    window.addToCart = function(id, description, category, imagePath) {
        let relativeImagePath = imagePath;
        if (relativeImagePath.startsWith('../')) {
            relativeImagePath = './' + relativeImagePath.substring(3);
        }

        const existingItem = cart.find(item => item.id === id);
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            cart.push({
                id: id,
                description: description,
                category: category,
                image_path: relativeImagePath,
                quantity: 1
            });
        }

        saveCart();
        renderCart();

        trackAnalyticsEvent('add_to_cart', {
            currency: 'USD',
            items: [{
                item_id: id,
                item_name: description,
                item_category: category,
                quantity: 1
            }]
        });
        trackAnalyticsEvent('agregar_al_carrito', {
            id_producto: id,
            nombre_producto: description,
            categoria: category,
            origen: 'pagina_producto_estatica'
        });

        // Animar el botón
        const btn = document.getElementById('btnAddProduct');
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.style.background = 'var(--accent-orange)';
            btn.style.borderColor = 'transparent';
            btn.style.color = '#ffffff';
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor; margin-right: 8px;">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
                ¡Agregado a la lista!
            `;
            setTimeout(() => {
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.color = '';
                btn.innerHTML = originalHTML;
            }, 1200);
        }

        // Animar FAB
        const badgeEl = document.getElementById('fabCartBadge');
        if (badgeEl) {
            badgeEl.style.transform = 'scale(1.4)';
            setTimeout(() => {
                badgeEl.style.transform = '';
            }, 300);
        }
    };

    window.updateCartQty = function(id, delta) {
        const item = cart.find(item => item.id === id);
        if (!item) return;

        item.quantity += delta;
        if (item.quantity <= 0) {
            cart = cart.filter(item => item.id !== id);
        }
        saveCart();
        renderCart();
    };

    window.removeFromCart = function(id) {
        cart = cart.filter(item => item.id !== id);
        saveCart();
        renderCart();
    };

    function renderCart() {
        const container = document.getElementById('cartItemsContainer');
        const totalItemsEl = document.getElementById('cartTotalItems');
        const badgeEl = document.getElementById('fabCartBadge');

        if (!container || !totalItemsEl || !badgeEl) return;

        let totalQty = 0;

        if (cart.length === 0) {
            container.innerHTML = `
                <div class="cart-empty">
                    <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 48px; height: 48px; fill: var(--text-muted); opacity: 0.5;">
                        <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
                    </svg>
                    <p style="margin-top: 12px; font-size: 13px; color: var(--text-muted);">Tu lista de pedido está vacía</p>
                    <span style="font-size: 11px; color: var(--text-muted)">Agrega piezas usando el botón "Añadir"</span>
                </div>
            `;
        } else {
            let html = '';
            cart.forEach(item => {
                totalQty += item.quantity;
                
                let displayImgPath = item.image_path;
                if (displayImgPath.startsWith('./')) {
                    displayImgPath = '../' + displayImgPath.substring(2);
                } else if (displayImgPath.startsWith('assets/')) {
                    displayImgPath = '../' + displayImgPath;
                }

                html += `
                    <div class="cart-item" id="cart-item-${item.id}">
                        <img src="${displayImgPath}" alt="${item.description}" class="cart-item-img" width="60" height="60" loading="lazy">
                        <div class="cart-item-info">
                            <span class="cart-item-category">${item.category}</span>
                            <div class="cart-item-title" title="${item.description}">${item.description}</div>
                            <div class="cart-item-controls">
                                <button class="cart-qty-btn" onclick="updateCartQty('${item.id}', -1)" aria-label="Disminuir cantidad">-</button>
                                <span class="cart-item-qty">${item.quantity}</span>
                                <button class="cart-qty-btn" onclick="updateCartQty('${item.id}', 1)" aria-label="Incrementar cantidad">+</button>
                            </div>
                        </div>
                        <button class="cart-item-remove" onclick="removeFromCart('${item.id}')" aria-label="Eliminar repuesto">
                            <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 18px; height: 18px; fill: currentColor;">
                                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                            </svg>
                        </button>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        const clearBtn = document.getElementById('cartClearBtn');
        if (clearBtn) {
            clearBtn.style.display = cart.length === 0 ? 'none' : 'block';
        }

        totalItemsEl.innerText = totalQty;
        badgeEl.innerText = totalQty;

        if (totalQty > 0) {
            badgeEl.classList.add('active');
        } else {
            badgeEl.classList.remove('active');
        }
    }

    function sendCartToWhatsApp() {
        if (cart.length === 0) {
            toggleCart(false);
            return;
        }

        trackAnalyticsEvent('generate_lead', {
            currency: 'USD',
            value: 0,
            items: cart.map(i => ({ item_id: i.id, item_name: i.description, item_category: i.category, quantity: i.quantity }))
        });
        trackAnalyticsEvent('enviar_pedido_whatsapp', {
            origen: 'cart_drawer_static',
            total_items: cart.reduce((acc, i) => acc + i.quantity, 0)
        });

        let msg = `¡Hola TODO PARTES HORIZONTE! Vengo desde su catálogo web y me gustaría cotizar la disponibilidad y precio de los siguientes repuestos:\n\n`;
        cart.forEach((item, index) => {
            msg += `*${index + 1}.*  ${item.description}\n`;
            msg += `    *Cantidad:* ${item.quantity} pc(s) | *Categoría:* _${item.category}_\n\n`;
        });
        msg += `Quedo atento a su respuesta. ¡Muchas gracias!`;

        const waMsgEncoded = encodeURIComponent(msg);
        const waUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${waMsgEncoded}`;
        window.open(waUrl, '_blank');
    }

    function setupEventListeners() {
        const prodHeading = document.querySelector('.product-title, h1');
        const prodCat = document.querySelector('.product-category');
        if (prodHeading) {
            trackAnalyticsEvent('view_item', {
                item_name: prodHeading.textContent.trim(),
                item_category: prodCat ? prodCat.textContent.trim() : ''
            });
        }

        const directWaBtn = document.querySelector('a[href*="wa.me"]');
        if (directWaBtn) {
            directWaBtn.addEventListener('click', () => {
                trackAnalyticsEvent('consultar_producto_whatsapp', {
                    origen: 'pagina_producto_estatica',
                    nombre_producto: prodHeading ? prodHeading.textContent.trim() : ''
                });
            });
        }

        const fab = document.getElementById('fabWhatsapp');
        if (fab) {
            fab.addEventListener('click', (e) => {
                e.preventDefault();
                trackAnalyticsEvent('begin_checkout', {
                    origen: 'fab_button_static'
                });
                toggleCart();
            });
        }

        const closeBtn = document.getElementById('cartCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toggleCart(false);
            });
        }

        const overlay = document.getElementById('cartOverlay');
        if (overlay) {
            overlay.addEventListener('click', () => {
                toggleCart(false);
            });
        }

        const submitBtn = document.getElementById('cartSubmitBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                sendCartToWhatsApp();
            });
        }

        const clearBtn = document.getElementById('cartClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                clearCart();
            });
        }
    }
})();
