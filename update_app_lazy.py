import re

with open('app.js', 'r', encoding='utf-8') as f:
    data = f.read()

# Add globals
globals_injection = """let hasNavigatedWithinApp = false;

        // Paginacion Infinita
        let currentFilteredProducts = [];
        let currentProductIndex = 0;
        const productsPerPage = 20;
        let productObserver = null;"""

data = data.replace('let hasNavigatedWithinApp = false;', globals_injection)

# Replace function
old_render = re.search(r'(?s)function renderProducts\(\) \{.*?(?=// Apertura del Lightbox Modal)', data).group(0)

new_render = """function renderProducts(reset = true) {
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
                        const terms = normalizedQuery.split(/\\s+/).filter(t => t.length > 0);
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
                    `¡Hola! Estoy interesado en el repuesto: *${product.description}* (Categoría: *${product.category}*).\\n¿Tienen disponibilidad y precio?\\nEnlace: ${cardUrl}`
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
"""

data = data.replace(old_render, new_render)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(data)
print("Updated app.js successfully!")
