// Cart manager for static product detail pages (sincronizado con app.js)
(function() {
    const WHATSAPP_NUMBER = "584242116375";
    const WA_ICON_PATH = "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z";
    let cart = [];

    function formatBs(amount) {
        if (amount == null || isNaN(amount)) return "Bs. 0,00";
        return "Bs. " + Number(amount).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function escapeHtmlAttr(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

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
        fab.setAttribute("aria-label", "Ver lista de cotización o escribir por WhatsApp");
        fab.innerHTML = `
            <div class="fab-cart-badge" id="fabCartBadge">0</div>
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="${WA_ICON_PATH}"/>
            </svg>
            <span class="fab-whatsapp-text" id="fabWhatsappText">¿Dudas? WhatsApp</span>
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
                <div id="cartDeliveryMount"></div>
                <button class="cart-submit-btn" id="cartSubmitBtn">
                    <svg viewBox="0 0 24 24" aria-hidden="true" style="width: 20px; height: 20px; fill: #fff; margin-right: 8px;">
                        <path d="${WA_ICON_PATH}"/>
                    </svg>
                    <span id="cartSubmitLabel">Enviar Pedido por WhatsApp</span>
                </button>
                <div style="font-size: 11px; color: var(--text-muted); text-align: center; line-height: 1.45;">
                    Pagos: <strong style="color: var(--text-secondary);">Pago Móvil · Transferencia Bancaria · Efectivo</strong> · Precios en Bs. al día ·
                    <a href="/politicas" style="color: var(--accent-orange); text-decoration: none;">Políticas de devolución</a>
                </div>
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
            const storedCart = localStorage.getItem('tph_cart') || sessionStorage.getItem('tph_cart');
            if (storedCart) {
                cart = JSON.parse(storedCart);
            }
        } catch (e) {
            console.error("Error al cargar el carrito:", e);
            cart = [];
        }
        renderCart();
    }

    function saveCart() {
        try {
            localStorage.setItem('tph_cart', JSON.stringify(cart));
        } catch (e) {
            console.error("Error al guardar el carrito:", e);
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

    window.addToCart = function(id, description, category, imagePath, variantData) {
        let relativeImagePath = imagePath || '';
        if (relativeImagePath.startsWith('../')) {
            relativeImagePath = './' + relativeImagePath.substring(3);
        }

        const v = variantData && typeof variantData === 'object' ? variantData : null;
        const brand = v && (v.brand || v.marca) ? String(v.brand || v.marca).trim() : null;
        const medida = v && v.medida ? String(v.medida).trim() : null;
        const lado = v && v.lado ? String(v.lado).trim() : null;
        const tipo = v && v.tipo ? String(v.tipo).trim() : null;
        const priceBs = v && Number(v.price_bs) > 0 ? Number(v.price_bs) : 0;
        const cartItemId = `${id}_${brand || ''}_${medida || ''}_${lado || ''}_${tipo || ''}`;

        const existingItem = cart.find(item => (item.cartItemId && item.cartItemId === cartItemId) || (!item.cartItemId && !brand && !medida && !lado && !tipo && item.id === id));
        if (existingItem) {
            existingItem.quantity += 1;
            existingItem.cartItemId = cartItemId;
            if (!existingItem.brand && brand) existingItem.brand = brand;
            if (!existingItem.medida && medida) existingItem.medida = medida;
            if (!existingItem.lado && lado) existingItem.lado = lado;
            if (!existingItem.tipo && tipo) existingItem.tipo = tipo;
            if (!existingItem.price_bs && priceBs) existingItem.price_bs = priceBs;
        } else {
            cart.push({
                cartItemId: cartItemId,
                id: id,
                description: description,
                category: category,
                image_path: relativeImagePath,
                brand: brand,
                medida: medida,
                lado: lado,
                tipo: tipo,
                price_bs: priceBs,
                quantity: 1
            });
        }

        saveCart();
        renderCart();

        trackAnalyticsEvent('add_to_cart', {
            currency: 'VES',
            value: priceBs,
            origen: 'ficha_seo',
            image_path: relativeImagePath,
            items: [{
                item_id: id,
                item_name: description,
                item_category: category,
                item_variant: brand || '',
                price: priceBs,
                quantity: 1
            }]
        });

        const btn = document.getElementById('btnAddProduct');
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.style.background = 'var(--accent-orange)';
            btn.style.borderColor = 'transparent';
            btn.style.color = '#ffffff';
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor; margin-right: 6px;">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
                <span>¡Agregado!</span>
            `;
            setTimeout(() => {
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.color = '';
                btn.innerHTML = originalHTML;
            }, 1200);
        }

        const badgeEl = document.getElementById('fabCartBadge');
        if (badgeEl) {
            badgeEl.style.transform = 'scale(1.4)';
            setTimeout(() => {
                badgeEl.style.transform = '';
            }, 300);
        }
    };

    window.updateCartQty = function(cartItemId, delta) {
        const item = cart.find(item => (item.cartItemId || item.id) === cartItemId);
        if (!item) return;

        item.quantity += delta;
        if (item.quantity <= 0) {
            cart = cart.filter(i => (i.cartItemId || i.id) !== cartItemId);
        }
        saveCart();
        renderCart();
    };

    window.removeFromCart = function(cartItemId) {
        cart = cart.filter(item => (item.cartItemId || item.id) !== cartItemId);
        saveCart();
        renderCart();
    };

    function renderCart() {
        const container = document.getElementById('cartItemsContainer');
        const totalItemsEl = document.getElementById('cartTotalItems');
        const badgeEl = document.getElementById('fabCartBadge');
        const fabTextEl = document.getElementById('fabWhatsappText');
        const submitLabelEl = document.getElementById('cartSubmitLabel');

        if (!container || !totalItemsEl || !badgeEl) return;

        let totalQty = 0;
        let totalBs = 0;

        if (cart.length === 0) {
            const prodTitle = document.querySelector('h1.product-title, h1');
            const prodName = prodTitle ? prodTitle.textContent.trim() : '';
            const directMsg = prodName
                ? `¡Hola TODO PARTES HORIZONTE! Tengo una duda sobre el repuesto *${prodName}*. ¿Me pueden asesorar?`
                : `¡Hola TODO PARTES HORIZONTE! Vengo desde su catálogo web y tengo una consulta sobre un repuesto.`;
            const directWaHref = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(directMsg)}`;
            container.innerHTML = `
                <div class="cart-empty">
                    <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 48px; height: 48px; fill: var(--text-muted); opacity: 0.5;">
                        <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
                    </svg>
                    <p style="margin-top: 12px; font-size: 13.5px; color: var(--text-secondary);">Tu lista de pedido está vacía</p>
                    <span style="font-size: 12px; color: var(--text-muted); max-width: 260px;">Agrega varios repuestos para cotizar juntos, o escríbenos directo si tienes dudas de compatibilidad.</span>
                    <a href="${directWaHref}" target="_blank" rel="noopener noreferrer" onclick="if(typeof trackEvent==='function')trackEvent('contacto_whatsapp',{origen:'cart_empty_direct'})" style="margin-top: 12px; display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 12px; background: rgba(37, 211, 102, 0.14); border: 1px solid rgba(37, 211, 102, 0.4); color: #25d366; text-decoration: none; font-size: 13px; font-weight: 700;">
                        <svg viewBox="0 0 24 24" aria-hidden="true" style="width: 16px; height: 16px; fill: currentColor; opacity: 1;"><path d="${WA_ICON_PATH}"/></svg>
                        <span>Escribir duda por WhatsApp</span>
                    </a>
                </div>
            `;
        } else {
            let html = '';
            cart.forEach(item => {
                const cId = item.cartItemId || item.id;
                totalQty += item.quantity;
                const itemSubtotalBs = (item.price_bs || 0) * item.quantity;
                totalBs += itemSubtotalBs;

                let displayImgPath = item.image_path || '';
                if (displayImgPath.startsWith('./')) {
                    displayImgPath = '../' + displayImgPath.substring(2);
                } else if (displayImgPath.startsWith('assets/')) {
                    displayImgPath = '../' + displayImgPath;
                }

                const variantDetails = [];
                if (item.brand) variantDetails.push(`Marca: <strong>${escapeHtmlAttr(item.brand)}</strong>`);
                if (item.lado) variantDetails.push(`Lado: <strong>${escapeHtmlAttr(item.lado)}</strong>`);
                if (item.tipo) variantDetails.push(`Tipo: <strong>${escapeHtmlAttr(item.tipo)}</strong>`);
                if (item.medida) variantDetails.push(`Medida: <strong>${escapeHtmlAttr(item.medida)}</strong>`);
                const variantStr = variantDetails.length > 0 ? `<div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${variantDetails.join(' · ')}</div>` : '';
                const priceStr = item.price_bs ? `<div style="font-size: 12px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${formatBs(itemSubtotalBs)}</div>` : '';
                const safeCIdAttr = escapeHtmlAttr(cId);

                html += `
                    <div class="cart-item" id="cart-item-${safeCIdAttr}">
                        <img src="${escapeHtmlAttr(displayImgPath)}" alt="${escapeHtmlAttr(item.description)}" class="cart-item-img" width="60" height="60" loading="lazy" onerror="if(!this.dataset.retried){this.dataset.retried='1';this.src=this.src.split('?')[0]+'?v='+Date.now();}">
                        <div class="cart-item-info">
                            <span class="cart-item-category">${escapeHtmlAttr(item.category)}</span>
                            <div class="cart-item-title" title="${escapeHtmlAttr(item.description)}">${escapeHtmlAttr(item.description)}</div>
                            ${variantStr}
                            ${priceStr}
                            <div class="cart-item-controls" style="margin-top: 6px;">
                                <button class="cart-qty-btn" onclick="updateCartQty('${safeCIdAttr}', -1)" aria-label="Disminuir cantidad">-</button>
                                <span class="cart-item-qty">${item.quantity}</span>
                                <button class="cart-qty-btn" onclick="updateCartQty('${safeCIdAttr}', 1)" aria-label="Incrementar cantidad">+</button>
                            </div>
                        </div>
                        <button class="cart-item-remove" onclick="removeFromCart('${safeCIdAttr}')" aria-label="Eliminar repuesto">
                            <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 18px; height: 18px; fill: currentColor;">
                                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                            </svg>
                        </button>
                    </div>
                `;
            });

            const deliveryFeeBs = (window.TPHDelivery && typeof window.TPHDelivery.getDeliveryFeeBs === 'function')
                ? window.TPHDelivery.getDeliveryFeeBs('cart')
                : 0;
            if (totalBs > 0 || deliveryFeeBs > 0) {
                const allPriced = cart.length > 0 && cart.every(i => Number(i.price_bs) > 0);
                const totalLabel = deliveryFeeBs > 0
                    ? (allPriced ? 'Repuestos:' : 'Subtotal repuestos:')
                    : (allPriced ? 'Total del Pedido:' : 'Subtotal Confirmado:');
                const itemsRow = totalBs > 0 ? `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">${totalLabel}</span>
                        <span style="font-size: 18px; font-weight: 800; color: #ffffff; font-family: 'Outfit', sans-serif;">${formatBs(totalBs)}</span>
                    </div>
                ` : '';
                const deliveryRow = deliveryFeeBs > 0 ? `
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; color: #6ee7a8; margin-top: ${totalBs > 0 ? '6px' : '0'};">
                        <span>Delivery zona:</span>
                        <strong>+${formatBs(deliveryFeeBs)}</strong>
                    </div>
                    ${totalBs > 0 ? `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 8px; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.12);">
                        <span style="font-size: 13px; font-weight: 800; color: #ffffff; text-transform: uppercase;">${allPriced ? 'Total con Delivery:' : 'Subtotal con Delivery:'}</span>
                        <span style="font-size: 18px; font-weight: 800; color: #6ee7a8; font-family: 'Outfit', sans-serif;">${formatBs(totalBs + deliveryFeeBs)}</span>
                    </div>` : ''}
                ` : '';
                html += `
                    <div style="padding: 14px; background: rgba(255, 106, 0, 0.08); border: 1px solid rgba(255, 106, 0, 0.2); border-radius: 10px; margin-top: 12px;">
                        ${itemsRow}
                        ${deliveryRow}
                    </div>
                `;
            }

            container.innerHTML = html;
        }

        const clearBtn = document.getElementById('cartClearBtn');
        if (clearBtn) {
            clearBtn.style.display = cart.length === 0 ? 'none' : 'block';
        }

        totalItemsEl.innerText = totalQty;
        badgeEl.innerText = totalQty;
        if (fabTextEl) {
            fabTextEl.innerText = totalQty > 0 ? `Ver Pedido (${totalQty})` : '¿Dudas? WhatsApp';
        }
        if (submitLabelEl) {
            submitLabelEl.innerText = totalQty > 0 ? 'Enviar Pedido por WhatsApp' : 'Consultar duda por WhatsApp';
        }

        if (totalQty > 0) {
            badgeEl.classList.add('active');
        } else {
            badgeEl.classList.remove('active');
        }
    }

    function sendCartToWhatsApp() {
        if (cart.length === 0) {
            const prodTitle = document.querySelector('h1.pp-title, h1.product-title, h1');
            const prodName = prodTitle ? prodTitle.textContent.trim() : '';
            const msg = prodName
                ? `¡Hola TODO PARTES HORIZONTE! Tengo una consulta sobre el repuesto *${prodName}*. ¿Me pueden asesorar?`
                : `¡Hola TODO PARTES HORIZONTE! Vengo desde su catálogo web y me gustaría consultar por un repuesto.`;
            trackAnalyticsEvent('contacto_whatsapp', { origen: 'cart_empty_cta' });
            window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(msg)}`, '_blank');
            return;
        }

        if (window.TPHDelivery && typeof window.TPHDelivery.validate === 'function') {
            const check = window.TPHDelivery.validate('cart');
            if (!check.valid) return;
        }

        let totalBs = 0;
        let totalQty = 0;
        let pricedCount = 0;
        cart.forEach(item => {
            totalQty += item.quantity;
            if (Number(item.price_bs) > 0) pricedCount += 1;
        });
        const allPriced = pricedCount === cart.length;

        let msg = allPriced
            ? `¡Hola TODO PARTES HORIZONTE! Quiero realizar el siguiente pedido desde su catálogo web:\n\n`
            : pricedCount > 0
                ? `¡Hola TODO PARTES HORIZONTE! Quiero armar el siguiente pedido desde su catálogo web:\n\n`
                : `¡Hola TODO PARTES HORIZONTE! Vengo desde su catálogo web y quiero confirmar precio y disponibilidad de:\n\n`;

        cart.forEach((item, index) => {
            const unitBs = Number(item.price_bs) || 0;
            const subtotalBs = unitBs * item.quantity;
            totalBs += subtotalBs;

            const details = [];
            if (item.brand) details.push(`Marca: ${item.brand}`);
            if (item.lado) details.push(`Lado: ${item.lado}`);
            if (item.tipo) details.push(`Tipo: ${item.tipo}`);
            if (item.medida) details.push(`Medida: ${item.medida}`);

            const qtyStr = unitBs > 0 && item.quantity > 1
                ? `Cant.: ${item.quantity} (${formatBs(unitBs)} c/u)`
                : `Cant.: ${item.quantity}`;
            const pricePart = unitBs > 0 ? `*${formatBs(subtotalBs)}*` : `Precio: Por confirmar`;

            const metaParts = [];
            if (details.length > 0) metaParts.push(details.join(' · '));
            metaParts.push(qtyStr);
            metaParts.push(pricePart);

            msg += `*${index + 1}.* ${item.description}\n`;
            msg += `   • ${metaParts.join(' | ')}\n\n`;
        });

        const deliveryAddon = (window.TPHDelivery && typeof window.TPHDelivery.formatWhatsAppAddon === 'function')
            ? window.TPHDelivery.formatWhatsAppAddon('cart', totalBs)
            : '';
        const itemWord = totalQty === 1 ? '1 repuesto' : `${totalQty} repuestos`;
        if (allPriced && totalBs > 0) {
            msg += `*Total (${itemWord}):* ${formatBs(totalBs)}\n`;
            if (deliveryAddon) msg += `${deliveryAddon}\n`;
            msg += `\n¿Me confirman disponibilidad y los datos de pago para concretar la compra? ¡Gracias!`;
        } else if (totalBs > 0) {
            msg += `*Subtotal confirmado:* ${formatBs(totalBs)} _(faltan repuestos por confirmar precio)_\n`;
            if (deliveryAddon) msg += `${deliveryAddon}\n`;
            msg += `\n¿Me confirman disponibilidad y el total final para concretar la compra? ¡Gracias!`;
        } else {
            if (deliveryAddon) msg += `${deliveryAddon}\n\n`;
            msg += `Quedo atento a su respuesta para concretar la compra. ¡Gracias!`;
        }

        trackAnalyticsEvent('enviar_pedido_whatsapp', {
            currency: 'VES',
            value: totalBs,
            origen: 'cart_checkout',
            total_items: cart.reduce((acc, i) => acc + i.quantity, 0),
            items: cart.map(i => ({ item_id: i.id, item_name: i.description, item_category: i.category, quantity: i.quantity }))
        });

        const waMsgEncoded = encodeURIComponent(msg);
        const waUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${waMsgEncoded}`;
        window.open(waUrl, '_blank');
    }

    function setupEventListeners() {
        const fabBtn = document.getElementById('fabWhatsapp');
        if (fabBtn) {
            fabBtn.addEventListener('click', (e) => {
                e.preventDefault();
                toggleCart();
            });
        }

        const closeBtn = document.getElementById('cartCloseBtn');
        if (closeBtn) closeBtn.addEventListener('click', () => toggleCart(false));

        const overlay = document.getElementById('cartOverlay');
        if (overlay) overlay.addEventListener('click', () => toggleCart(false));

        const cartDeliveryMount = document.getElementById('cartDeliveryMount');
        if (cartDeliveryMount && window.TPHDelivery) {
            window.TPHDelivery.mount('cart', cartDeliveryMount, {
                basePath: '../',
                onChange: () => renderCart()
            });
        }

        const submitBtn = document.getElementById('cartSubmitBtn');
        if (submitBtn) submitBtn.addEventListener('click', sendCartToWhatsApp);
    }

    function trackAnalyticsEvent(eventName, params = {}) {
        try {
            if (typeof window.trackEvent === 'function') {
                window.trackEvent(eventName, params);
                return;
            }
            if (typeof gtag === 'function') {
                gtag('event', eventName, params);
            }
            if (typeof fbq === 'function') {
                if (eventName === 'add_to_cart' || eventName === 'agregar_al_carrito') {
                    fbq('track', 'AddToCart', {
                        content_name: params.nombre_producto || (params.items && params.items[0] ? params.items[0].item_name : ''),
                        currency: 'VES'
                    });
                } else if (eventName === 'enviar_pedido_whatsapp' || eventName === 'generate_lead') {
                    fbq('track', 'Lead', { content_name: 'Pedido WhatsApp', currency: 'VES' });
                    fbq('track', 'Contact');
                }
            }
        } catch (e) {}
    }
})();
