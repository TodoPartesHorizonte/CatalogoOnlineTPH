// Configuración Global
        let WHATSAPP_NUMBER = "584242116375";
        let productsData = [];
        let activeCategory = "ALL";
        let activeVehicle = "ALL";
        let searchQuery = "";
        let activeView = "FOLDERS"; // Empezar por carpetas por defecto
        window.currentProductId = null;
        let hasNavigatedWithinApp = false;

        // Paginacion Infinita
        let currentFilteredProducts = [];
        let currentProductIndex = 0;
        const productsPerPage = 20;
        let productObserver = null;

        // Estado del Carrito y Funciones de Soporte
        let cart = [];

        // Normaliza texto eliminando acentos para búsqueda insensible a tildes
        function normalizeText(text) {
            if (!text) return '';
            return text.toString()
                       .toLowerCase()
                       .normalize("NFD")
                       .replace(/[\u0300-\u036f]/g, "") // Remueve diacríticos
                       .replace(/[^a-z0-9\s]/g, ""); // Deja solo letras, números y espacios
        }

        // Inicializar carrito cargándolo de sessionStorage (mantiene los datos por sesión)
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

        // Guardar estado del carrito
        function saveCart() {
            try {
                sessionStorage.setItem('tph_cart', JSON.stringify(cart));
            } catch (e) {
                console.error("Error al guardar el carrito en sessionStorage:", e);
            }
        }

        // Vaciar todo el carrito con confirmación
        window.clearCart = function() {
            if (confirm("¿Estás seguro de que deseas vaciar toda tu lista de pedido?")) {
                cart = [];
                saveCart();
                renderCart();
                toggleCart(false); // Cierra el cajón al vaciar
            }
        };

        // Alternar el cajón del carrito
        function toggleCart(forceOpen) {
            const drawer = document.getElementById('cartDrawer');
            const overlay = document.getElementById('cartOverlay');
            if (!drawer || !overlay) return;

            const isOpen = typeof forceOpen === 'boolean' ? forceOpen : !drawer.classList.contains('active');

            if (isOpen) {
                drawer.classList.add('active');
                overlay.classList.add('active');
                document.body.style.overflow = 'hidden'; // Evita scroll de fondo
            } else {
                drawer.classList.remove('active');
                overlay.classList.remove('active');
                
                // Restaurar el scroll del cuerpo solo si el lightbox tampoco está abierto
                const lightboxEl = document.getElementById('lightbox');
                const isLightboxActive = lightboxEl && lightboxEl.classList.contains('active');
                if (!isLightboxActive) {
                    document.body.style.overflow = '';
                }
            }
        }

        // Agregar producto al carrito
        function addToCart(productId) {
            const product = productsData.find(p => p.id === productId);
            if (!product) return;

            // Increment feedback interaction
            incrementInteractionCount();

            const existingItem = cart.find(item => item.id === productId);
            if (existingItem) {
                existingItem.quantity += 1;
            } else {
                cart.push({
                    id: product.id,
                    description: product.description,
                    category: product.category,
                    image_path: product.image_path,
                    quantity: 1
                });
            }

            saveCart();
            renderCart();

            // Rastrear evento en GA4
            trackEvent('agregar_al_carrito', {
                items: [{
                    item_id: product.id,
                    item_name: product.description,
                    item_category: product.category,
                    quantity: 1
                }],
                descripcion: 'Se agregó un producto al carrito de compras',
                origen: 'catalogo_page'
            });

            // Animación visual del botón que corresponda
            animateAddToCartBtn(productId);
            animateFabBadge();
        }

        // Quitar un producto del carrito
        function removeFromCart(productId) {
            cart = cart.filter(item => item.id !== productId);
            saveCart();
            renderCart();
        }

        // Modificar cantidad (+1 o -1)
        function updateCartQty(productId, delta) {
            const item = cart.find(item => item.id === productId);
            if (!item) return;

            item.quantity += delta;
            if (item.quantity <= 0) {
                removeFromCart(productId);
            } else {
                saveCart();
                renderCart();
            }
        }

        // Renderizar dinámicamente los elementos dentro del carrito
        function renderCart() {
            const container = document.getElementById('cartItemsContainer');
            const totalItemsEl = document.getElementById('cartTotalItems');
            const badgeEl = document.getElementById('fabCartBadge');

            if (!container || !totalItemsEl || !badgeEl) return;

            let totalQty = 0;

            if (cart.length === 0) {
                container.innerHTML = `
                    <div class="cart-empty">
                        <svg aria-hidden="true" viewBox="0 0 24 24">
                            <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
                        </svg>
                        <p>Tu lista de pedido está vacía</p>
                        <span style="font-size: 12px; color: var(--text-muted)">Agrega piezas usando el botón "Añadir"</span>
                    </div>
                `;
            } else {
                let html = '';
                cart.forEach(item => {
                    totalQty += item.quantity;
                    html += `
                        <div class="cart-item" id="cart-item-${item.id}">
                            <img src="${item.image_path}" alt="${item.description}" class="cart-item-img" width="60" height="60" loading="lazy">
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
                                <svg aria-hidden="true" viewBox="0 0 24 24">
                                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                                </svg>
                            </button>
                        </div>
                    `;
                });
                container.innerHTML = html;
            }

            // Mostrar/ocultar botón de vaciar
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

        // Animar el botón de agregar
        function animateAddToCartBtn(productId) {
            // Buscar tanto en tarjetas del catálogo como en el lightbox modal
            const btns = [
                document.getElementById(`btn-add-${productId}`),
                document.getElementById('lightboxAddBtn')
            ];

            btns.forEach(btn => {
                if (!btn) return;
                const isLightboxBtn = btn.id === 'lightboxAddBtn';
                const originalHTML = btn.innerHTML;

                btn.style.background = 'var(--accent-orange)';
                btn.style.color = '#ffffff';
                btn.innerHTML = `
                    <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor;">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                    <span>${isLightboxBtn ? '¡Agregado a la lista!' : '¡Agregado!'}</span>
                `;

                setTimeout(() => {
                    btn.style.background = '';
                    btn.style.color = '';
                    btn.innerHTML = originalHTML;
                }, 1200);
            });
        }

        // Efecto visual de rebote en el FAB
        function animateFabBadge() {
            const badgeEl = document.getElementById('fabCartBadge');
            if (!badgeEl) return;
            
            badgeEl.style.transform = 'scale(1.4)';
            setTimeout(() => {
                badgeEl.style.transform = '';
            }, 300);
        }

        // Construir el mensaje de cotización consolidado y enviar a WhatsApp
        function sendCartToWhatsApp() {
            if (cart.length === 0) {
                toggleCart(false);
                return;
            }

            let msg = `¡Hola TODO PARTES HORIZONTE! Vengo desde su catálogo web y me gustaría cotizar la disponibilidad y precio de los siguientes repuestos:\n\n`;
            cart.forEach((item, index) => {
                msg += `*${index + 1}.*  ${item.description}\n`;
                msg += `    *Cantidad:* ${item.quantity} pc(s) | *Categoría:* _${item.category}_\n\n`;
            });
            msg += `Quedo atento a su respuesta. ¡Muchas gracias!`;

            // Rastrear checkout en Analytics
            trackEvent('enviar_pedido_whatsapp', {
                cantidad_items: cart.length,
                descripcion: 'El usuario envió un pedido al WhatsApp de la tienda',
                origen: 'catalogo_page'
            });

            const waMsgEncoded = encodeURIComponent(msg);
            const waUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${waMsgEncoded}`;
            window.open(waUrl, '_blank');
        }

        // Sincronizar el estado actual del catálogo con la URL de la barra del navegador
        function syncStateToURL(pushNewState = false) {
            const params = new URLSearchParams();
            if (activeVehicle && activeVehicle !== 'ALL') {
                params.set('vehiculo', activeVehicle);
            }
            if (activeCategory && activeCategory !== 'ALL') {
                params.set('categoria', activeCategory);
            }
            if (searchQuery && searchQuery.trim() !== '') {
                params.set('buscar', searchQuery);
            }
            if (activeView && activeView !== 'FOLDERS') {
                params.set('vista', activeView);
            }
            
            const isLightboxActive = lightbox && lightbox.classList.contains('active');
            if (isLightboxActive && window.currentProductId) {
                const p = productsData.find(prod => prod.id === window.currentProductId);
                params.set('producto', p && p.slug ? p.slug : window.currentProductId);
            }

            const queryString = params.toString() ? '?' + params.toString() : '';
            const newUrl = window.location.pathname + queryString;

            const stateData = {
                view: activeView,
                category: activeCategory,
                vehicle: activeVehicle,
                search: searchQuery,
                lightbox: isLightboxActive,
                productId: window.currentProductId || null
            };

            if (pushNewState) {
                history.pushState(stateData, "", newUrl);
                hasNavigatedWithinApp = true;
            } else {
                if (window.location.search !== queryString) {
                    history.replaceState(stateData, "", newUrl);
                }
            }
        }

        // Cargar y reconstruir el estado visual en base a los parámetros de la URL
        function parseURLState() {
            const urlParams = new URLSearchParams(window.location.search);
            const initVehicle = urlParams.get('vehiculo') || 'ALL';
            const initCategory = urlParams.get('categoria') || 'ALL';
            const initSearch = urlParams.get('buscar') || '';
            const initView = urlParams.get('vista') || 'FOLDERS';
            const initProduct = urlParams.get('producto');

            activeVehicle = initVehicle;
            activeCategory = initCategory;
            searchQuery = initSearch;
            if (searchInput) searchInput.value = initSearch;

            // Actualizar clases activas en los botones de vehículos
            document.querySelectorAll('.vehicle-card').forEach(card => {
                card.classList.remove('active');
            });
            const filterId = `vehicle-${activeVehicle.toLowerCase().replace('-', '')}`;
            const activeCard = document.getElementById(filterId);
            if (activeCard) activeCard.classList.add('active');

            // Actualizar píldoras de categorías activas
            renderCategories();

             if (initView === 'PHOTOS' || initCategory !== 'ALL' || initSearch !== '') {
                activeView = 'PHOTOS';
                if (btnViewPhotos) btnViewPhotos.classList.add('active');
                if (btnViewFolders) btnViewFolders.classList.remove('active');
                if (categoriesScrollContainer) categoriesScrollContainer.style.display = 'none';
                if (productsGrid) productsGrid.style.display = 'grid';
                if (foldersGrid) foldersGrid.style.display = 'none';
                renderProducts();
                
                const navBack = document.getElementById('navBackContainer');
                if (navBack) {
                    navBack.style.display = 'flex';
                }
                const viewTitle = document.getElementById('currentViewTitle');
                if (viewTitle) {
                    viewTitle.innerText = activeCategory === 'ALL' ? 'Catálogo' : activeCategory;
                }
                
                // Activar pill en el scroll de categorías
                document.querySelectorAll('.category-pill').forEach(pill => {
                    if (pill.getAttribute('data-category') === activeCategory) {
                        pill.classList.add('active');
                    } else {
                        pill.classList.remove('active');
                    }
                });
            } else {
                // Vista de carpetas
                activeView = 'FOLDERS';
                if (btnViewPhotos) btnViewPhotos.classList.remove('active');
                if (btnViewFolders) btnViewFolders.classList.add('active');
                if (categoriesScrollContainer) categoriesScrollContainer.style.display = 'none';
                if (productsGrid) productsGrid.style.display = 'none';
                if (foldersGrid) foldersGrid.style.display = 'grid';
                const navBack = document.getElementById('navBackContainer');
                if (navBack) {
                    navBack.style.display = 'none';
                }
                renderFolders();
            }

            // Control de lightbox
            if (initProduct) {
                const matchedProduct = productsData.find(p => p.slug === initProduct || p.id === initProduct);
                if (matchedProduct) {
                    window.currentProductId = matchedProduct.id;
                    openLightboxDirect(matchedProduct.id);
                } else {
                    closeLightboxDirect();
                }
            } else {
                closeLightboxDirect();
            }
        }

        // Abre el modal directamente sin empujar estados de historial redundantes
        function openLightboxDirect(productId) {
            const product = productsData.find(p => p.id === productId);
            if (!product) return;

            // Increment feedback interaction
            incrementInteractionCount();

            lightboxImg.src = product.image_path;
            lightboxImg.alt = product.description;
            lightboxBadge.innerText = product.category;
            lightboxDesc.innerText = product.description;

            // Actualizar título y metadatos dinámicamente para indexabilidad SEO de Google
            window.originalTitle = window.originalTitle || document.title;
            const descMeta = document.querySelector('meta[name="description"]');
            window.originalDesc = window.originalDesc || (descMeta ? descMeta.getAttribute('content') : '');
            
            document.title = `${product.description} | TODO PARTES HORIZONTE`;
            if (descMeta) {
                descMeta.setAttribute('content', `Consigue ${product.description} en TODO PARTES HORIZONTE. Repuesto de categoría ${product.category}. Consulta disponibilidad por WhatsApp.`);
            }
            
            const cardUrl = `${window.location.origin}${window.location.pathname}?producto=${product.slug || productId}`;
            const waMsg = encodeURIComponent(
                `¡Hola! Estoy interesado en el repuesto: *${product.description}* (Categoría: *${product.category}*).\n¿Tienen disponibilidad y precio?\nEnlace: ${cardUrl}`
            );
            lightboxActionBtn.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${waMsg}`;
            
            // Rastrear evento en GA4
            trackEvent('ver_detalle_producto', {
                item_id: product.id,
                item_name: product.description,
                item_category: product.category,
                origen: 'catalogo_page'
            });

            // Asignar evento al botón de agregar en el lightbox
            const lightboxAddBtn = document.getElementById('lightboxAddBtn');
            if (lightboxAddBtn) {
                lightboxAddBtn.onclick = () => {
                    addToCart(productId);
                };
            }

            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function matchesVehicleFilter(product, filter) {
            if (filter === 'ALL') return true;
            
            const desc = normalizeText(product.description);
            const keywords = (product.keywords || []).map(k => normalizeText(k));
            
            if (filter === 'CARIBE') {
                return desc.includes('caribe') || keywords.includes('caribe');
            }
            if (filter === 'LUV') {
                const isDMax = desc.includes('d-max') || desc.includes('dmax') || keywords.includes('d-max') || keywords.includes('dmax');
                const isLuv = desc.includes('luv') || keywords.includes('luv');
                return isLuv && !isDMax;
            }
            if (filter === 'D-MAX') {
                return desc.includes('d-max') || desc.includes('dmax') || keywords.includes('d-max') || keywords.includes('dmax');
            }
            if (filter === 'TROOPER') {
                return desc.includes('trooper') || keywords.includes('trooper');
            }
            if (filter === 'RODEO') {
                return desc.includes('rodeo') || keywords.includes('rodeo');
            }
            return true;
        }

        window.selectVehicleFilter = function(filter) {
            activeVehicle = filter;
            
            trackEvent('filtrar_vehiculo', {
                vehicle_name: filter,
                origen: 'catalogo_page'
            });

            
            // Actualizar clases activas en los botones de vehículos
            document.querySelectorAll('.vehicle-card').forEach(card => {
                card.classList.remove('active');
            });
            const filterId = `vehicle-${filter.toLowerCase().replace('-', '')}`;
            const activeCard = document.getElementById(filterId);
            if (activeCard) activeCard.classList.add('active');
            
            // Re-renderizar categorías y el contenido
            renderCategories();
            
            if (activeView === 'PHOTOS') {
                renderProducts();
            } else {
                renderFolders();
            }

            syncStateToURL(false);
        };

        // Elementos del DOM
        const searchInput = document.getElementById('searchInput');
        const categoriesScroll = document.getElementById('categoriesScroll');
        const productsGrid = document.getElementById('productsGrid');
        const foldersGrid = document.getElementById('foldersGrid');
        const categoriesScrollContainer = document.getElementById('categoriesScrollContainer');
        const btnViewPhotos = document.getElementById('btnViewPhotos');
        const btnViewFolders = document.getElementById('btnViewFolders');
        const emptyState = document.getElementById('emptyState');
        const lightbox = document.getElementById('lightbox');
        const lightboxClose = document.getElementById('lightboxClose');
        const lightboxImg = document.getElementById('lightboxImg');
        const lightboxBadge = document.getElementById('lightboxBadge');
        const lightboxDesc = document.getElementById('lightboxDesc');
        const lightboxActionBtn = document.getElementById('lightboxActionBtn');
        const fabWhatsapp = document.getElementById('fabWhatsapp');

        // Inicialización
        document.addEventListener('DOMContentLoaded', () => {
            fetchProducts();
            setupEventListeners();
            initFeedbackModal();
        });

        // Carga de Datos desde products.js (cargado como script global PRODUCTS_DATA)
        async function fetchProducts() {
            try {
                if (typeof PRODUCTS_DATA === 'undefined') {
                    throw new Error('PRODUCTS_DATA no está definido.');
                }
                const data = PRODUCTS_DATA;
                
                // Actualizar configuración
                productsData = data.products || [];
                WHATSAPP_NUMBER = deobfuscate(data.whatsapp_number) || WHATSAPP_NUMBER;
                
                // Mostrar logo personalizado si existe (ya inicializado por script inline)
                if (data.use_custom_logo) {
                    const logoImg = document.getElementById('logoImage');
                    if (logoImg) {
                        logoImg.src = data.use_custom_logo;
                        logoImg.style.display = 'block';
                    }
                }
                
                // Renderizar redes sociales y contacto (Opción A)
                renderSocialLinks(data);

                // Configurar FAB General de WhatsApp
                const catalogUrl = window.location.href.split('?')[0];
                const generalMsg = encodeURIComponent(`¡Hola! Vengo desde el catálogo online y me gustaría hacer una consulta.`);
                fabWhatsapp.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${generalMsg}`;

                // Mostrar contenedor de filtro de vehículos
                const vehicleFilterContainer = document.getElementById('vehicleFilterContainer');
                if (vehicleFilterContainer) {
                    vehicleFilterContainer.style.display = 'block';
                }

                // Reconstruir estado inicial desde la URL
                parseURLState();

                // Inicializar Carrito desde localStorage
                initCart();
            } catch (error) {
                console.error('Error al inicializar el catálogo:', error);
                productsGrid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--accent-orange)">
                        <p style="font-weight: 700; font-size: 18px;">Error al cargar el catálogo de productos</p>
                        <p style="font-size: 14px; margin-top: 8px; color: var(--text-secondary)">Asegúrate de haber ejecutado el script de sincronización local.</p>
                    </div>
                `;
            }
        }

        // Renderizado de Categorías
        function renderCategories() {
            // Filtrar productos solo por el vehículo activo (y buscador) para obtener los conteos de categorías
            const vehicleFiltered = productsData.filter(product => {
                const matchesVehicle = matchesVehicleFilter(product, activeVehicle);
                
                let matchesSearch = true;
                if (searchQuery.trim() !== '') {
                    const normalizedQuery = normalizeText(searchQuery);
                    const terms = normalizedQuery.split(/\s+/).filter(t => t.length > 0);
                    matchesSearch = terms.every(term => {
                        const inDesc = normalizeText(product.description).includes(term);
                        const inCat = normalizeText(product.category).includes(term);
                        const inKeywords = (product.keywords || []).some(k => normalizeText(k).includes(term));
                        return inDesc || inCat || inKeywords;
                    });
                }
                return matchesVehicle && matchesSearch;
            });

            // Contar productos por categoría
            const counts = {};
            vehicleFiltered.forEach(p => {
                counts[p.category] = (counts[p.category] || 0) + 1;
            });


            // Generar HTML de categorías
            let html = `
                <button class="category-pill ${activeCategory === 'ALL' ? 'active' : ''}" data-category="ALL" id="cat-all">
                    Ver Todo <span>${vehicleFiltered.length}</span>
                </button>
            `;

            // Ordenar categorías alfabéticamente
            const categories = Object.keys(counts).sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));
            
            categories.forEach(cat => {
                html += `
                    <button class="category-pill ${activeCategory === cat ? 'active' : ''}" data-category="${cat}" id="cat-${cat.replace(/\s+/g, '-')}">
                        ${cat} <span>${counts[cat]}</span>
                    </button>
                `;
            });

            categoriesScroll.innerHTML = html;

            // Registrar eventos de clic para los filtros
            document.querySelectorAll('.category-pill').forEach(pill => {
                pill.addEventListener('click', (e) => {
                    document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
                    const selectedPill = e.currentTarget;
                    selectedPill.classList.add('active');
                    
                    activeCategory = selectedPill.getAttribute('data-category');
                    
                    trackEvent('filtrar_categoria', {
                        category_name: activeCategory,
                        origen: 'catalogo_page'
                    });

                    // Increment feedback interaction
                    incrementInteractionCount();

                    renderProducts();
                    
                    // Desplazar pill seleccionada al centro en móviles
                    selectedPill.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                    
                    syncStateToURL(false);
                    window.scrollTo({ top: 0, behavior: 'instant' });
                });
            });
        }

        // Renderizado de Productos
        function renderProducts(reset = true) {
            if (reset) {
                // Filtrar productos
                currentFilteredProducts = productsData.filter(product => {
                    // Filtro por categoría
                    const matchesCategory = activeCategory === 'ALL' || product.category === activeCategory;
                    
                    // Filtro por vehículo
                    const matchesVehicle = matchesVehicleFilter(product, activeVehicle);

                    // Filtro por buscador (búsqueda multi-término)
                    let matchesSearch = true;
                    if (searchQuery.trim() !== '') {
                        const normalizedQuery = normalizeText(searchQuery);
                        const terms = normalizedQuery.split(/\s+/).filter(t => t.length > 0);
                        matchesSearch = terms.every(term => {
                            const inDesc = normalizeText(product.description).includes(term);
                            const inCat = normalizeText(product.category).includes(term);
                            const inKeywords = (product.keywords || []).some(k => normalizeText(k).includes(term));
                            return inDesc || inCat || inKeywords;
                        });
                    }
                    
                    return matchesCategory && matchesVehicle && matchesSearch;
                });

                // Si no hay productos, mostrar estado vacío
                if (currentFilteredProducts.length === 0) {
                    productsGrid.style.display = 'none';
                    emptyState.style.display = 'flex';
                    return;
                }

                productsGrid.style.display = 'grid';
                emptyState.style.display = 'none';
                productsGrid.innerHTML = '';
                currentProductIndex = 0;

                // Desconectar observer previo si existe
                if (productObserver) {
                    productObserver.disconnect();
                }
            }

            // Obtener el siguiente lote de productos
            const nextBatch = currentFilteredProducts.slice(currentProductIndex, currentProductIndex + productsPerPage);
            if (nextBatch.length === 0) return;

            // Generar HTML de las tarjetas
            let gridHtml = '';
            nextBatch.forEach((product, index) => {
                let isLcp = reset && index < 4;
                let imgPriority = isLcp ? 'fetchpriority="high"' : 'loading="lazy"';
                
                // Prefila el mensaje de consulta de WhatsApp
                const cardUrl = `${window.location.origin}${window.location.pathname}?producto=${product.slug || product.id}`;
                const waMsg = encodeURIComponent(
                    `¡Hola! Estoy interesado en el repuesto: *${product.description}* (Categoría: *${product.category}*).\n¿Tienen disponibilidad y precio?\nEnlace: ${cardUrl}`
                );
                const whatsappLink = `https://wa.me/${WHATSAPP_NUMBER}?text=${waMsg}`;

                gridHtml += `
                    <div class="product-card" id="card-${product.id}">
                        <div class="card-img-wrapper" onclick="openLightbox('${product.id}')" role="button" tabindex="0" aria-label="Ver detalles del repuesto">
                            <span class="category-badge">${product.category}</span>
                            <img src="${product.image_path}" alt="${product.description}" class="product-img img-lazy" ${imgPriority} width="280" height="350" onload="this.classList.add('img-loaded')">
                        </div>
                        <div class="card-content">
                            <div class="product-desc" title="${product.description}">${product.description}</div>
                            <div class="card-actions">
                                <a href="${whatsappLink}" target="_blank" class="card-btn" id="btn-wa-${product.id}" aria-label="Consultar repuesto por WhatsApp">
                                    <svg aria-hidden="true" viewBox="0 0 24 24">
                                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                                    </svg>
                                    <span>Consultar</span>
                                </a>
                                <button class="card-btn-add" id="btn-add-${product.id}" onclick="event.stopPropagation(); addToCart('${product.id}')" aria-label="Añadir a la lista de pedido">
                                    <svg aria-hidden="true" viewBox="0 0 24 24">
                                        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                                    </svg>
                                    <span>Añadir</span>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            productsGrid.insertAdjacentHTML('beforeend', gridHtml);
            currentProductIndex += nextBatch.length;

            // Configurar el IntersectionObserver para cargar más si aún hay productos
            if (currentProductIndex < currentFilteredProducts.length) {
                const lastCard = productsGrid.lastElementChild;
                
                productObserver = new IntersectionObserver((entries) => {
                    if (entries[0].isIntersecting) {
                        productObserver.unobserve(lastCard);
                        renderProducts(false); // Cargar siguiente página
                    }
                }, {
                    rootMargin: '200px' // Cargar 200px antes de llegar al final
                });
                
                productObserver.observe(lastCard);
            }
        }
// Apertura del Lightbox Modal
        window.openLightbox = function(productId) {
            window.currentProductId = productId;
            openLightboxDirect(productId);
            syncStateToURL(true);
        };

        // Cierre del Lightbox Modal (mediante historial o directo)
        function closeLightbox() {
            const urlParams = new URLSearchParams(window.location.search);
            if (hasNavigatedWithinApp && urlParams.has('producto')) {
                history.back();
            } else {
                closeLightboxDirect();
                syncStateToURL(false);
                parseURLState();
            }
        }

        // Cierre directo del DOM del Lightbox
        function closeLightboxDirect() {
            lightbox.classList.remove('active');
            document.body.style.overflow = ''; // Restaurar scroll
            window.currentProductId = null;

            // Restaurar título y metadatos SEO por defecto
            if (window.originalTitle) {
                document.title = window.originalTitle;
            }
            const descMeta = document.querySelector('meta[name="description"]');
            if (descMeta && window.originalDesc) {
                descMeta.setAttribute('content', window.originalDesc);
            }

            setTimeout(() => {
                if (!lightbox.classList.contains('active')) {
                    lightboxImg.src = '';
                }
            }, 300);
        }

        // Alternar entre vista de fotos y vista de carpetas
        function switchView(view) {
            activeView = view;
            
            if (activeView === 'PHOTOS') {
                if (btnViewPhotos) btnViewPhotos.classList.add('active');
                if (btnViewFolders) btnViewFolders.classList.remove('active');
                
                categoriesScrollContainer.style.display = 'none';
                productsGrid.style.display = 'grid';
                foldersGrid.style.display = 'none';
                
                renderProducts();
            } else {
                if (btnViewPhotos) btnViewPhotos.classList.remove('active');
                if (btnViewFolders) btnViewFolders.classList.add('active');
                
                categoriesScrollContainer.style.display = 'none';
                productsGrid.style.display = 'none';
                foldersGrid.style.display = 'grid';
                
                // Ocultar botón de volver al estar en el menú principal de carpetas
                document.getElementById('navBackContainer').style.display = 'none';
                
                renderFolders();
            }
            window.scrollTo({ top: 0, behavior: 'instant' });
        }

        // Renderizado de Carpetas (Categorías como tarjetas visuales)
        function renderFolders() {
            // Filtrar productos por vehículo y buscador
            const vehicleFiltered = productsData.filter(product => {
                const matchesVehicle = matchesVehicleFilter(product, activeVehicle);
                
                let matchesSearch = true;
                if (searchQuery.trim() !== '') {
                    const normalizedQuery = normalizeText(searchQuery);
                    const terms = normalizedQuery.split(/\s+/).filter(t => t.length > 0);
                    matchesSearch = terms.every(term => {
                        const inDesc = normalizeText(product.description).includes(term);
                        const inCat = normalizeText(product.category).includes(term);
                        const inKeywords = (product.keywords || []).some(k => normalizeText(k).includes(term));
                        return inDesc || inCat || inKeywords;
                    });
                }
                return matchesVehicle && matchesSearch;
            });

            const counts = {};
            vehicleFiltered.forEach(p => {
                counts[p.category] = (counts[p.category] || 0) + 1;
            });

            const categories = Object.keys(counts).sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));

            if (categories.length === 0) {
                foldersGrid.style.display = 'none';
                emptyState.style.display = 'flex';
                return;
            }

            foldersGrid.style.display = 'grid';
            emptyState.style.display = 'none';

            let foldersHtml = '';
            categories.forEach((cat, index) => {
                const count = counts[cat];
                const countText = count === 1 ? '1 repuesto' : `${count} repuestos`;
                const folderId = `folder-${cat.replace(/\s+/g, '-')}`;
                // Variar sutilmente el angulo del degradado por tarjeta
                const gradAngle = 120 + (index % 5) * 15;

                foldersHtml += `
                    <div class="category-card" onclick="selectFolderCategory('${cat.replace(/'/g, "\\'")}')" id="${folderId}" role="button" tabindex="0" aria-label="Ver categoría ${cat}">
                        <div class="category-card-bg-layer" style="background: url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='49' viewBox='0 0 28 49'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%23ff6a00' fill-opacity='0.025'%3E%3Cpath d='M13.99 9.25l13 7.5v15l-13 7.5L1 31.75v-15l12.99-7.5zM3 17.9v12.7l10.99 6.34 11-6.35V17.9l-11-6.34L3 17.9zM0 15l12.98-7.5V0h-2v6.35L0 12.69v2.3zm0 18.5L12.98 41v8h-2v-6.85L0 35.81v-2.3zM15 0v7.5L27.99 15H28v-2.31h-.01L17 6.35V0h-2zm0 49v-8l12.99-7.5H28v2.31h-.01L17 42.15V49h-2z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E&quot;), linear-gradient(${gradAngle}deg, #0d0d10 0%, #141418 50%, rgba(255, 106, 0, 0.06) 100%)"></div>
                        <svg class="category-card-icon" aria-hidden="true" viewBox="0 0 24 24">
                            <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                        </svg>
                        <div class="category-card-count-badge">${count}</div>
                        <div class="category-card-content">
                            <div class="category-card-name">${cat}</div>
                            <div class="category-card-subtitle">${countText}</div>
                        </div>
                    </div>
                `;
            });

            foldersGrid.innerHTML = foldersHtml;

            // Ajustar tamaño de fuente dinámicamente
            requestAnimationFrame(() => { resizeFolderCardNames(); });
        }

        // Función reutilizable para ajustar tipografía dinámica de carpetas
        function resizeFolderCardNames() {
            // Deshabilitado para mantener tipografía uniforme y legible en todo el catálogo (controlado por CSS)
        }

        // Selección de carpeta desde la vista de carpetas
        window.selectFolderCategory = function(category) {
            activeCategory = category;
            activeView = 'PHOTOS';
            syncStateToURL(true);
            parseURLState();
            window.scrollTo({ top: 0, behavior: 'instant' });
            
            // Increment feedback interaction
            incrementInteractionCount();
        };

        // Retorno al menú de carpetas (con soporte de navegación)
        window.goBackToFolders = function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (hasNavigatedWithinApp && (urlParams.has('categoria') || urlParams.has('buscar') || urlParams.has('producto'))) {
                history.back();
            } else {
                activeCategory = 'ALL';
                activeView = 'FOLDERS';
                searchQuery = '';
                if (searchInput) searchInput.value = '';
                syncStateToURL(false);
                parseURLState();
                window.scrollTo({ top: 0, behavior: 'instant' });
            }
        };

        function goBackToFoldersDirect() {
            activeCategory = 'ALL';
            searchQuery = '';
            searchInput.value = '';
            
            activeView = 'FOLDERS';
            categoriesScrollContainer.style.display = 'none';
            productsGrid.style.display = 'none';
            foldersGrid.style.display = 'grid';
            
            document.getElementById('navBackContainer').style.display = 'none';
            renderFolders();
        }

        // Manejador del botón físico de atrás en el teléfono (popstate)
        window.addEventListener('popstate', (event) => {
            parseURLState();
        });

        // Renderizar enlaces de contacto y redes en cabecera (Opción A)
        function renderSocialLinks(data) {
            const container = document.getElementById('socialLinksHeader');
            if (!container) return;
            
            let html = `
                <a href="./informacion.html" class="contact-link home-btn" title="Conoce más sobre nosotros" onclick="trackEvent('clic_ver_informacion', { origen: 'catalogo_header' })">
                    <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                    <span>Nosotros</span>
                </a>
            `;
            
            // Decodificar enlaces y número antes de renderizar
            const whatsappNum = deobfuscate(data.whatsapp_number);
            const instagramUrl = deobfuscate(data.instagram_url);
            const facebookUrl = deobfuscate(data.facebook_url);
            const mapsUrl = deobfuscate(data.maps_url);
            const reviewsUrl = deobfuscate(data.reviews_url);
            
            // WhatsApp
            if (whatsappNum) {
                const generalMsg = encodeURIComponent(`¡Hola! Vengo desde el catálogo online y me gustaría hacer una consulta.`);
                html += `
                    <a href="https://wa.me/${whatsappNum}?text=${generalMsg}" target="_blank" class="contact-link whatsapp" title="WhatsApp" onclick="trackEvent('contacto_whatsapp', { origen: 'catalogo_header' })">
                        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>
                        <span>WhatsApp</span>
                    </a>
                `;
            }
            
            // Instagram
            if (instagramUrl) {
                html += `
                    <a href="${instagramUrl}" target="_blank" class="contact-link instagram" title="Instagram" onclick="trackEvent('clic_redes_sociales', { red_social: 'instagram', origen: 'catalogo_header' })">
                        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.051.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
                        <span>Instagram</span>
                    </a>
                `;
            }
            
            // Facebook
            if (facebookUrl) {
                html += `
                    <a href="${facebookUrl}" target="_blank" class="contact-link facebook" title="Facebook" onclick="trackEvent('clic_redes_sociales', { red_social: 'facebook', origen: 'catalogo_header' })">
                        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                        <span>Facebook</span>
                    </a>
                `;
            }
            
            // Google Maps
            if (mapsUrl) {
                html += `
                    <a href="${mapsUrl}" target="_blank" class="contact-link google-maps" title="Ubicación" onclick="trackEvent('clic_ver_mapa', { origen: 'catalogo_header' })">
                        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 0C7.802 0 4.4 3.402 4.4 7.602C4.4 13.01 12 24 12 24S19.6 13.01 19.6 7.602C19.6 3.402 16.198 0 12 0ZM12 10.4C10.454 10.4 9.2 9.146 9.2 7.6C9.2 6.054 10.454 4.8 12 4.8C13.546 4.8 14.8 6.054 14.8 7.6C14.8 9.146 13.546 10.4 12 10.4Z"/></svg>
                        <span>Ubicación</span>
                    </a>
                `;
            }
            
            // Google Reviews
            if (reviewsUrl) {
                html += `
                    <a href="${reviewsUrl}" target="_blank" class="contact-link google-reviews" title="Opiniones Google" onclick="trackEvent('clic_ver_resenas', { origen: 'catalogo_header' })">
                        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
                        <span>Opiniones</span>
                    </a>
                `;
            }
            
            container.innerHTML = html;
        }

        // Registro de Eventos
        function setupEventListeners() {
            // Evento Buscador (Búsqueda en tiempo real)
            searchInput.addEventListener('change', (e) => {
                if (e.target.value.trim() !== '') {
                    trackEvent('buscar_producto', {
                        search_term: e.target.value,
                        origen: 'catalogo_page'
                    });
                    // Increment feedback interaction
                    incrementInteractionCount();
                }
            });

            searchInput.addEventListener('input', (e) => {
                const oldQuery = searchQuery;
                searchQuery = e.target.value;
                if (searchQuery.trim() !== '') {
                    const wasFolders = activeView === 'FOLDERS';
                    activeCategory = 'ALL';
                    activeView = 'PHOTOS';
                    
                    syncStateToURL(false);
                    
                    document.getElementById('navBackContainer').style.display = 'flex';
                    document.getElementById('currentViewTitle').innerText = `Buscando: "${searchQuery}"`;
                    
                    categoriesScrollContainer.style.display = 'none';
                    productsGrid.style.display = 'grid';
                    foldersGrid.style.display = 'none';
                    
                    renderProducts();
                    
                    if (wasFolders || oldQuery.trim() === '') {
                        window.scrollTo({ top: 0, behavior: 'instant' });
                    }
                } else {
                    // Volver a carpetas al borrar
                    activeCategory = 'ALL';
                    activeView = 'FOLDERS';
                    syncStateToURL(false);
                    parseURLState();
                    window.scrollTo({ top: 0, behavior: 'instant' });
                }
            });

            // Cambiar de vista (Fotos / Carpetas)
            if (btnViewPhotos) {
                btnViewPhotos.addEventListener('click', () => {
                    activeView = 'PHOTOS';
                    syncStateToURL(true);
                    parseURLState();
                });
            }
            if (btnViewFolders) {
                btnViewFolders.addEventListener('click', () => {
                    activeView = 'FOLDERS';
                    activeCategory = 'ALL';
                    syncStateToURL(true);
                    parseURLState();
                });
            }

            // Cerrar Lightbox con botón
            lightboxClose.addEventListener('click', closeLightbox);

            // Cerrar Lightbox al hacer clic fuera del contenido
            lightbox.addEventListener('click', (e) => {
                if (e.target === lightbox) {
                    closeLightbox();
                }
            });

            // Cerrar con tecla Escape
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && lightbox.classList.contains('active')) {
                    closeLightbox();
                }
            });

            // Colapso dinámico de cabecera al hacer scroll (Totalmente estable con wrapper de altura fija y sin saltos)
            const headerEl = document.querySelector('header');
            const wrapperEl = document.querySelector('.header-wrapper');
            let lastWidth = window.innerWidth;
            let heightDiff = 170; // valor por defecto seguro

            function adjustWrapperHeight() {
                const isFixed = window.getComputedStyle(headerEl).position === 'fixed';
                if (isFixed) {
                    const wasCollapsed = headerEl.classList.contains('collapsed');
                    if (wasCollapsed) headerEl.classList.remove('collapsed');
                    
                    const fullHeight = headerEl.offsetHeight;
                    wrapperEl.style.height = `${fullHeight}px`;
                    
                    // Forzar cálculo de la altura colapsada
                    headerEl.classList.add('collapsed');
                    const collapsedHeight = headerEl.offsetHeight;
                    heightDiff = fullHeight - collapsedHeight;
                    
                    // Restaurar el estado original anterior
                    if (!wasCollapsed) headerEl.classList.remove('collapsed');
                } else {
                    wrapperEl.style.height = '';
                    heightDiff = 0;
                }
            }
            
            // Medir y ajustar al cargar y al cambiar de tamaño horizontal (evitando bug de redimensionamiento de barra de dirección en móvil)
            setTimeout(adjustWrapperHeight, 150);
            
            window.addEventListener('resize', () => {
                if (window.innerWidth !== lastWidth) {
                    lastWidth = window.innerWidth;
                    adjustWrapperHeight();
                    resizeFolderCardNames();
                }
            });

            window.addEventListener('scroll', () => {
                // El colapso se activa exactamente cuando la página se ha desplazado el equivalente a la diferencia de altura, evitando huecos y saltos
                if (window.scrollY > heightDiff) {
                    headerEl.classList.add('collapsed');
                } else {
                    headerEl.classList.remove('collapsed');
                }
            }, { passive: true });

            // Eventos de control del Carrito
            const fabWhatsappBtn = document.getElementById('fabWhatsapp');
            if (fabWhatsappBtn) {
                fabWhatsappBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    toggleCart();
                });
            }

            const cartCloseBtn = document.getElementById('cartCloseBtn');
            if (cartCloseBtn) {
                cartCloseBtn.addEventListener('click', () => {
                    toggleCart(false);
                });
            }

            const cartOverlay = document.getElementById('cartOverlay');
            if (cartOverlay) {
                cartOverlay.addEventListener('click', () => {
                    toggleCart(false);
                });
            }

            const cartSubmitBtn = document.getElementById('cartSubmitBtn');
            if (cartSubmitBtn) {
                cartSubmitBtn.addEventListener('click', () => {
                    sendCartToWhatsApp();
                });
            }

            // Rastreo de click en botones de consultar directos (Catálogo)
            document.addEventListener('click', (e) => {
                const cardBtn = e.target.closest('.card-btn');
                if (cardBtn && cardBtn.id && cardBtn.id.startsWith('btn-wa-')) {
                    const productId = cardBtn.id.replace('btn-wa-', '');
                    const product = productsData.find(p => p.id === productId);
                    if (product) {
                        trackEvent('consultar_producto_whatsapp', {
                            item_name: product.description,
                            item_id: product.id,
                            origen: 'catalogo_page'
                        });
                        incrementInteractionCount();
                    }
                }
                
                // Track category clicks for feedback
                if (e.target.closest('.category-item')) {
                    incrementInteractionCount();
                }
            });

            // Rastreo de click en botón de consultar en Lightbox
            const lightboxActionBtn = document.getElementById('lightboxActionBtn');
            if (lightboxActionBtn) {
                lightboxActionBtn.addEventListener('click', () => {
                    if (window.currentProductId) {
                        const product = productsData.find(p => p.id === window.currentProductId);
                        if (product) {
                            trackEvent('consultar_producto_whatsapp', {
                                item_name: product.description,
                                item_id: product.id,
                                origen: 'catalogo_lightbox',
                                descripcion: 'Clic en consultar desde el Lightbox (ventana de detalles)'
                            });
                            incrementInteractionCount();
                        }
                    }
                });
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            initFeedbackModal();
        });

        /* ========================================================
           LÓGICA DEL MODAL FLOTANTE DE FEEDBACK Y REDES SOCIALES
           ======================================================== */
        const FEEDBACK_INTERACTIONS_KEY = "feedback_interaction_count";
        const FEEDBACK_SHOWN_KEY = "feedback_modal_shown";
        const INTERACTIONS_THRESHOLD = 3; // Trigger after 3 interactions

        function incrementInteractionCount() {
            if (localStorage.getItem(FEEDBACK_SHOWN_KEY) === "true") return;

            let count = parseInt(localStorage.getItem(FEEDBACK_INTERACTIONS_KEY) || "0", 10);
            count++;
            localStorage.setItem(FEEDBACK_INTERACTIONS_KEY, count.toString());

            if (count >= INTERACTIONS_THRESHOLD) {
                showFeedbackModal();
            }
        }

        function initFeedbackModal() {
            if (localStorage.getItem(FEEDBACK_SHOWN_KEY) === "true") return;
            const overlay = document.getElementById('feedbackModalOverlay');
            if (overlay) {
                overlay.style.display = 'none';
                overlay.classList.remove('active');
            }
        }

        function showFeedbackModal() {
            const overlay = document.getElementById('feedbackModalOverlay');
            const content = document.getElementById('feedbackModalContent');
            const card = document.getElementById('feedbackModalCard');
            if (!overlay || !content || !card) return;

            if (typeof PRODUCTS_DATA === 'undefined') return;
            
            const whatsappNum = deobfuscate(PRODUCTS_DATA.whatsapp_number);
            const instagramUrl = deobfuscate(PRODUCTS_DATA.instagram_url);
            const facebookUrl = deobfuscate(PRODUCTS_DATA.facebook_url);
            const reviewsUrl = deobfuscate(PRODUCTS_DATA.reviews_url);

            const variants = [];

            if (instagramUrl) {
                variants.push({
                    type: 'instagram',
                    title: '¡Síguenos en Instagram!',
                    text: 'Conoce nuestras novedades, fotos reales de repuestos Isuzu y tips de mantenimiento directamente en tu feed.',
                    buttonText: 'Seguir en Instagram',
                    url: instagramUrl,
                    icon: `<svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.051.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>`
                });
            }

            if (facebookUrl) {
                variants.push({
                    type: 'facebook',
                    title: '¡Únete a nuestra comunidad!',
                    text: 'Visítanos en Facebook para estar al tanto de ofertas especiales, consultas directas y novedades de nuestro inventario.',
                    buttonText: 'Visitar en Facebook',
                    url: facebookUrl,
                    icon: `<svg viewBox="0 0 24 24"><path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c4.56-.93 8-4.96 8-9.75z"/></svg>`
                });
            }

            if (whatsappNum) {
                const whatsappChatUrl = `https://wa.me/${whatsappNum}?text=${encodeURIComponent("Hola, me gustaría recibir asesoría técnica y cotizaciones rápidas sobre repuestos Isuzu.")}`;
                variants.push({
                    type: 'whatsapp',
                    title: '¿Necesitas asesoría técnica?',
                    text: 'Conversa directamente con nuestros especialistas en repuestos Isuzu y cotiza en segundos vía chat.',
                    buttonText: 'Chatear por WhatsApp',
                    url: whatsappChatUrl,
                    icon: `<svg viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946C.06 5.348 5.397.01 12.008.01c3.202.001 6.212 1.246 8.477 3.514 2.266 2.268 3.507 5.28 3.505 8.484-.004 6.657-5.34 11.997-11.953 11.997-2.005-.001-3.973-.502-5.724-1.455L0 24zm6.59-4.846c1.6.95 3.188 1.449 4.725 1.45 5.489 0 9.953-4.43 9.956-9.878.002-2.64-1.019-5.123-2.877-6.982C16.59 1.885 14.113.864 11.472.863 5.98 .863 1.519 5.293 1.516 10.741c-.002 1.624.437 3.208 1.272 4.607L1.82 21.05l5.827-1.526zM17.51 14.36c-.3-.149-1.772-.874-2.047-.973-.274-.1-.474-.149-.673.15-.199.299-.772.973-.947 1.172-.174.199-.349.224-.648.075-.3-.149-1.266-.467-2.41-1.485-.89-.793-1.492-1.773-1.666-2.07-.174-.3-.019-.462.13-.61.135-.133.3-.349.449-.523.149-.174.199-.299.299-.497.1-.2.05-.374-.025-.523-.075-.15-.673-1.62-.922-2.218-.242-.584-.487-.506-.673-.506-.174-.002-.374-.002-.573-.002-.2 0-.523.075-.797.373-.274.3-1.047 1.022-1.047 2.49 0 1.468 1.07 2.887 1.22 3.087.149.199 2.106 3.216 5.099 4.508.712.308 1.268.492 1.702.63.716.227 1.368.195 1.884.118.574-.085 1.772-.723 2.022-1.42.25-.697.25-1.294.174-1.42-.075-.126-.274-.199-.573-.349z"/></svg>`
                });
            }

            if (reviewsUrl) {
                variants.push({
                    type: 'google',
                    title: '¡Tu opinión nos importa mucho!',
                    text: '¿Te ha sido de utilidad este catálogo online? Déjanos una reseña corta en Google para seguir mejorando el servicio.',
                    buttonText: 'Dejar Opinión en Google',
                    url: reviewsUrl,
                    icon: `<svg viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L6.02 21z"/></svg>`
                });
            }

            if (variants.length === 0) return;

            const randomIndex = Math.floor(Math.random() * variants.length);
            const selected = variants[randomIndex];

            card.className = "feedback-modal-card";
            card.classList.add(`modal-variant-${selected.type}`);

            let modalHTML = '';

            if (selected.type === 'google') {
                modalHTML = `
                    <div class="feedback-modal-header">
                        <div class="feedback-modal-icon-container">
                            ${selected.icon}
                        </div>
                        <h3 class="feedback-modal-title">${selected.title}</h3>
                    </div>
                    <div class="feedback-modal-body">
                        <div id="feedbackRatingSection">
                            <p class="feedback-modal-text">${selected.text}</p>
                            <div class="feedback-stars-container" id="feedbackStarsContainer">
                                <span class="feedback-star" data-rating="1">&#9733;</span>
                                <span class="feedback-star" data-rating="2">&#9733;</span>
                                <span class="feedback-star" data-rating="3">&#9733;</span>
                                <span class="feedback-star" data-rating="4">&#9733;</span>
                                <span class="feedback-star" data-rating="5">&#9733;</span>
                            </div>
                            <div class="feedback-modal-actions">
                                <a href="${selected.url}" id="googleFeedbackBtn" target="_blank" rel="noopener noreferrer" class="feedback-btn-primary" onclick="handleFeedbackSubmit(true)">
                                    ${selected.buttonText}
                                </a>
                                <button class="feedback-btn-secondary" onclick="closeFeedbackModal()">Quizás más tarde</button>
                            </div>
                        </div>
                        <div class="feedback-success-state" id="feedbackSuccessState">
                            <div class="feedback-success-checkmark">&#10004;</div>
                            <h4 class="feedback-modal-title" style="color: #25d366; font-size: 18px;">¡Muchas gracias!</h4>
                            <p class="feedback-modal-text" style="margin-bottom: 0; font-size: 14px;">Tu valoración nos ayuda a seguir creciendo y ofreciéndote el mejor servicio.</p>
                        </div>
                    </div>
                `;
            } else {
                modalHTML = `
                    <div class="feedback-modal-header">
                        <div class="feedback-modal-icon-container">
                            ${selected.icon}
                        </div>
                        <h3 class="feedback-modal-title">${selected.title}</h3>
                    </div>
                    <div class="feedback-modal-body">
                        <p class="feedback-modal-text">${selected.text}</p>
                        <div class="feedback-modal-actions">
                            <a href="${selected.url}" target="_blank" rel="noopener noreferrer" class="feedback-btn-primary" onclick="handleFeedbackSubmit(false, '${selected.type}')">
                                ${selected.buttonText}
                            </a>
                            <button class="feedback-btn-secondary" onclick="closeFeedbackModal()">Quizás más tarde</button>
                        </div>
                    </div>
                `;
            }

            content.innerHTML = modalHTML;

            overlay.style.display = 'flex';
            overlay.offsetHeight;
            overlay.classList.add('active');

            trackEvent('ver_modal_feedback', { tipo_modal: selected.type });

            if (selected.type === 'google') {
                setupGoogleStars(selected.url);
            }
        }

        function setupGoogleStars(reviewsUrl) {
            const starsContainer = document.getElementById('feedbackStarsContainer');
            if (!starsContainer) return;

            const stars = starsContainer.querySelectorAll('.feedback-star');

            stars.forEach(star => {
                star.addEventListener('mouseover', () => {
                    const rating = parseInt(star.getAttribute('data-rating'), 10);
                    highlightStars(stars, rating);
                });

                star.addEventListener('mouseout', () => {
                    highlightStars(stars, 0);
                });

                star.addEventListener('click', () => {
                    const rating = parseInt(star.getAttribute('data-rating'), 10);
                    
                    if (rating >= 4) {
                        trackEvent('valoracion_estrellas_alta', { estrellas: rating });
                        window.open(reviewsUrl, '_blank', 'noopener,noreferrer');
                        showFeedbackSuccessState();
                    } else {
                        trackEvent('valoracion_estrellas_baja', { estrellas: rating });
                        showFeedbackSuccessState();
                    }
                });
            });
        }

        function highlightStars(stars, rating) {
            stars.forEach(star => {
                const starRating = parseInt(star.getAttribute('data-rating'), 10);
                if (starRating <= rating) {
                    star.classList.add('hovered');
                } else {
                    star.classList.remove('hovered');
                }
            });
        }

        function showFeedbackSuccessState() {
            const ratingSection = document.getElementById('feedbackRatingSection');
            const successSection = document.getElementById('feedbackSuccessState');
            if (ratingSection && successSection) {
                ratingSection.style.display = 'none';
                successSection.style.display = 'flex';
                localStorage.setItem(FEEDBACK_SHOWN_KEY, "true");
                setTimeout(closeFeedbackModal, 3000);
            }
        }

        window.handleFeedbackSubmit = function(isGoogle, type = '') {
            localStorage.setItem(FEEDBACK_SHOWN_KEY, "true");
            if (isGoogle) {
                trackEvent('conversion_feedback_google', { accion: 'clic_dejar_opinion' });
            } else {
                trackEvent(`conversion_feedback_${type}`, { accion: 'clic_enlace_social' });
            }
            setTimeout(closeFeedbackModal, 500);
        };

        window.closeFeedbackModal = function() {
            const overlay = document.getElementById('feedbackModalOverlay');
            if (!overlay) return;

            overlay.classList.remove('active');
            setTimeout(() => {
                overlay.style.display = 'none';
                localStorage.setItem(FEEDBACK_SHOWN_KEY, "true");
            }, 400);
        };
