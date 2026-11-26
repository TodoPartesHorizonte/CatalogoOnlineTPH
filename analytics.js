/**
 * Módulo unificado de telemetría (Cloudflare KV + GA4 + Meta Pixel)
 * Compatible con CSP 'self' y envío sin preflight CORS en navegación saliente.
 */
(function (global) {
    'use strict';

    var analyticsInitialized = false;
    var recentEvents = {};
    var DEDUP_TTL_MS = 600;

    function deobfuscate(val) {
        if (!val) return '';
        try {
            return atob(val);
        } catch (e) {
            return val;
        }
    }

    function forceInitAnalytics() {
        if (analyticsInitialized) return;
        analyticsInitialized = true;

        var dataObj = typeof global.PRODUCTS_DATA !== 'undefined' ? global.PRODUCTS_DATA : null;
        var gaId = '';
        var metaId = '';

        if (global.GA_ID) {
            gaId = String(global.GA_ID).trim();
        } else if (dataObj && dataObj.google_analytics_id) {
            gaId = deobfuscate(dataObj.google_analytics_id).trim();
        }

        if (global.META_PIXEL_ID) {
            metaId = String(global.META_PIXEL_ID).trim();
        } else if (dataObj && dataObj.meta_pixel_id) {
            metaId = deobfuscate(dataObj.meta_pixel_id).trim();
        }

        if (gaId && gaId.indexOf('G-') === 0 && !document.getElementById('ga-script')) {
            var script = document.createElement('script');
            script.id = 'ga-script';
            script.async = true;
            script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(gaId);
            document.head.appendChild(script);

            global.dataLayer = global.dataLayer || [];
            global.gtag = function () { global.dataLayer.push(arguments); };
            global.gtag('js', new Date());
            global.gtag('config', gaId);
        }

        if (metaId && !document.getElementById('meta-pixel-script')) {
            !function (f, b, e, v, n, t, s) {
                if (f.fbq) return;
                n = f.fbq = function () {
                    n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
                };
                if (!f._fbq) f._fbq = n;
                n.push = n;
                n.loaded = true;
                n.version = '2.0';
                n.queue = [];
                t = b.createElement(e);
                t.async = true;
                t.id = 'meta-pixel-script';
                t.src = v;
                s = b.getElementsByTagName(e)[0];
                s.parentNode.insertBefore(t, s);
            }(global, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');

            global.fbq('init', metaId);
            global.fbq('track', 'PageView');
        }
    }

    function getTrackEndpoint() {
        try {
            var host = (global.location && global.location.hostname) || '';
            if (
                host === 'todoparteshorizonte.com' ||
                host === 'www.todoparteshorizonte.com' ||
                host === 'todoparteshorizonte.pages.dev' ||
                host === 'localhost' ||
                host === '127.0.0.1' ||
                (host.length > 10 && host.slice(-10) === '.pages.dev')
            ) {
                return '/api/track-event';
            }
        } catch (e) {}
        return 'https://todoparteshorizonte.com/api/track-event';
    }

    function sendToCloudflare(payload) {
        var endpoint = getTrackEndpoint();
        var sent = false;

        try {
            if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
                var blob = new Blob([payload], { type: 'text/plain;charset=UTF-8' });
                sent = navigator.sendBeacon(endpoint, blob);
            }
        } catch (e) {
            sent = false;
        }

        if (!sent && typeof fetch === 'function') {
            try {
                fetch(endpoint, {
                    method: 'POST',
                    mode: 'cors',
                    headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
                    body: payload,
                    keepalive: true
                }).catch(function () {});
            } catch (e) {}
        }
    }

    function isDuplicate(key) {
        if (!key) return false;
        var now = Date.now();
        var prev = recentEvents[key];
        if (prev && (now - prev) < DEDUP_TTL_MS) {
            return true;
        }
        recentEvents[key] = now;
        var keys = Object.keys(recentEvents);
        if (keys.length > 40) {
            for (var i = 0; i < keys.length; i++) {
                if ((now - recentEvents[keys[i]]) > DEDUP_TTL_MS * 2) {
                    delete recentEvents[keys[i]];
                }
            }
        }
        return false;
    }

    function extractFirstItem(params) {
        return (params && Array.isArray(params.items) && params.items.length > 0 && params.items[0]) || null;
    }

    function buildCfPayload(eventName, params) {
        var p = params || {};
        var first = extractFirstItem(p);
        var cfEvent = null;
        var cfData = {};
        var dedupKey = '';

        if (eventName === 'ver_detalle_producto' || eventName === 'view_item') {
            cfEvent = 'product_view';
            cfData = {
                product_id: p.item_id || p.id || (first ? (first.item_id || first.id || '') : ''),
                product_name: p.item_name || p.nombre_producto || (first ? (first.item_name || first.nombre_producto || '') : ''),
                product_model: p.item_category || p.categoria || (first ? (first.item_category || first.categoria || '') : ''),
                product_photo: p.image_path || ''
            };
            dedupKey = cfData.product_id || cfData.product_name;
        } else if (eventName === 'add_to_cart' || eventName === 'agregar_al_carrito') {
            cfEvent = 'add_to_cart';
            cfData = {
                product_id: p.item_id || p.id || (first ? (first.item_id || first.id || '') : ''),
                product_name: p.nombre_producto || p.item_name || (first ? (first.item_name || first.nombre_producto || '') : ''),
                product_model: p.categoria || p.item_category || (first ? (first.item_category || first.categoria || '') : ''),
                product_photo: p.image_path || '',
                source: p.origen || p.source || 'catalogo_page'
            };
            dedupKey = (cfData.product_id || cfData.product_name) + '|' + cfData.source;
        } else if (
            eventName === 'consultar_producto_whatsapp' ||
            eventName === 'contacto_whatsapp' ||
            eventName === 'enviar_pedido_whatsapp' ||
            eventName === 'generate_lead'
        ) {
            cfEvent = 'whatsapp_click';
            var waSource = p.origen || p.source || (eventName === 'enviar_pedido_whatsapp' ? 'cart_checkout' : 'directo');
            cfData = {
                source: waSource,
                product_id: p.item_id || (first ? (first.item_id || first.id || '') : ''),
                product_name: p.nombre_producto || p.item_name || (first ? (first.item_name || first.nombre_producto || '') : ''),
                product_model: p.categoria || p.item_category || (first ? (first.item_category || first.categoria || '') : '')
            };
            if (Array.isArray(p.items) && p.items.length > 0) {
                cfData.items = p.items.map(function (it) {
                    return {
                        product_id: (it && (it.item_id || it.id)) || '',
                        product_name: (it && (it.item_name || it.nombre_producto)) || '',
                        product_model: (it && (it.item_category || it.categoria)) || ''
                    };
                });
            }
            dedupKey = waSource + '|' + cfData.product_id + '|' + (cfData.items ? cfData.items.length : 0);
        } else if (eventName === 'buscar_producto' || eventName === 'search') {
            cfEvent = 'search';
            cfData = {
                query: p.termino_busqueda || p.search_term || p.query || '',
                results_count: typeof p.results_count === 'number' ? p.results_count : null
            };
            dedupKey = String(cfData.query || '').toLowerCase() + '|' + String(cfData.results_count);
        } else if (eventName === 'filtrar_vehiculo' || eventName === 'filter_vehicle') {
            cfEvent = 'filter_vehicle';
            cfData = {
                model_slug: p.vehicle_name || p.model_slug || ''
            };
            dedupKey = cfData.model_slug;
        } else if (eventName === 'page_view' || eventName === 'visita_catalogo') {
            cfEvent = 'page_view';
            cfData = {
                path: p.path || (global.location && global.location.pathname) || '/'
            };
            dedupKey = cfData.path;
        } else if (eventName === 'compartir_producto') {
            cfEvent = 'secondary_action';
            cfData = { action: 'share', source: p.origen || p.source || '' };
            dedupKey = 'share|' + cfData.source + '|' + (p.item_id || '');
        } else if (eventName === 'copiar_oem') {
            cfEvent = 'secondary_action';
            cfData = { action: 'oem_copy', source: p.origen || p.source || '' };
            dedupKey = 'oem_copy|' + cfData.source + '|' + (p.codigo_oem || '');
        } else if (eventName === 'clic_redes_sociales') {
            var red = String(p.red_social || 'social').toLowerCase();
            cfEvent = 'secondary_action';
            cfData = { action: red, source: p.origen || p.source || '' };
            dedupKey = red + '|' + cfData.source;
        } else if (eventName === 'clic_ver_mapa') {
            cfEvent = 'secondary_action';
            cfData = { action: 'maps', source: p.origen || p.source || '' };
            dedupKey = 'maps|' + cfData.source;
        } else if (eventName === 'clic_ver_resenas') {
            cfEvent = 'secondary_action';
            cfData = { action: 'reviews', source: p.origen || p.source || '' };
            dedupKey = 'reviews|' + cfData.source;
        } else if (eventName === 'clic_llamar') {
            cfEvent = 'secondary_action';
            cfData = { action: 'phone_call', source: p.origen || p.source || '' };
            dedupKey = 'phone_call|' + cfData.source;
        } else if (eventName === 'guardar_contacto') {
            cfEvent = 'secondary_action';
            cfData = { action: 'save_contact', source: p.origen || p.source || '' };
            dedupKey = 'save_contact|' + cfData.source;
        } else if (eventName === 'activar_push') {
            cfEvent = 'secondary_action';
            cfData = { action: 'push_subscribe', source: p.origen || p.source || '' };
            dedupKey = 'push_subscribe|' + cfData.source;
        } else if (eventName === 'conversion_feedback_whatsapp') {
            cfEvent = 'whatsapp_click';
            cfData = { source: 'feedback_modal', product_id: '', product_name: 'Feedback WhatsApp', product_model: '' };
            dedupKey = 'feedback_modal|wa';
        } else if (eventName === 'conversion_feedback_google') {
            cfEvent = 'secondary_action';
            cfData = { action: 'reviews', source: 'feedback_modal' };
            dedupKey = 'reviews|feedback_modal';
        } else if (eventName === 'conversion_feedback_instagram') {
            cfEvent = 'secondary_action';
            cfData = { action: 'instagram', source: 'feedback_modal' };
            dedupKey = 'instagram|feedback_modal';
        } else if (eventName === 'conversion_feedback_facebook') {
            cfEvent = 'secondary_action';
            cfData = { action: 'facebook', source: 'feedback_modal' };
            dedupKey = 'facebook|feedback_modal';
        }

        return { cfEvent: cfEvent, cfData: cfData, dedupKey: dedupKey };
    }

    function trackEvent(eventName, params) {
        forceInitAnalytics();

        var p = params || {};
        try {
            var mapped = buildCfPayload(eventName, p);
            if (mapped.cfEvent) {
                var fullDedup = mapped.cfEvent + '|' + mapped.dedupKey;
                if (isDuplicate(fullDedup)) {
                    return;
                }
                sendToCloudflare(JSON.stringify({ event: mapped.cfEvent, data: mapped.cfData }));
            }
        } catch (e) {}

        if (typeof global.gtag === 'function') {
            global.gtag('event', eventName, p);
        }

        if (typeof global.fbq === 'function') {
            var first = extractFirstItem(p);
            var itemName = p.nombre_producto || p.item_name || (first ? (first.item_name || first.nombre_producto || '') : '');
            var itemCat = p.categoria || p.item_category || (first ? (first.item_category || first.categoria || '') : '');

            if (eventName === 'view_item' || eventName === 'ver_detalle_producto') {
                global.fbq('track', 'ViewContent', {
                    content_name: itemName,
                    content_category: itemCat,
                    currency: 'USD'
                });
            } else if (eventName === 'add_to_cart' || eventName === 'agregar_al_carrito') {
                global.fbq('track', 'AddToCart', {
                    content_name: itemName,
                    content_category: itemCat,
                    currency: 'USD'
                });
            } else if (eventName === 'enviar_pedido_whatsapp' || eventName === 'generate_lead') {
                global.fbq('track', 'Lead', { content_name: 'Pedido WhatsApp', currency: 'USD' });
                global.fbq('track', 'Contact');
            } else if (eventName === 'consultar_producto_whatsapp' || eventName === 'contacto_whatsapp') {
                global.fbq('track', 'Contact', { content_name: itemName || p.origen || 'Consulta WhatsApp' });
            } else if (eventName === 'buscar_producto' || eventName === 'search') {
                global.fbq('track', 'Search', { search_string: p.termino_busqueda || p.search_term || p.query || '' });
            } else {
                global.fbq('trackCustom', eventName, p);
            }
        }
    }

    global.deobfuscate = deobfuscate;
    global.deobfuscateAnalytics = deobfuscate;
    global.forceInitAnalytics = forceInitAnalytics;
    global.trackEvent = trackEvent;

    if (typeof global.addEventListener === 'function') {
        global.addEventListener('load', function () {
            setTimeout(forceInitAnalytics, 1500);
        });
    }
})(window);
