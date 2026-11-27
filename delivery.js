/* ============================================================================
   TODO PARTES HORIZONTE — Módulo de Delivery (GPS / Mapa) y Envíos Nacionales
   Reutilizable entre Carrito (#cartDrawer), Lightbox (#lightbox) y Fichas /p/
   ============================================================================ */
(function (global) {
    'use strict';

    const DRAFT_STORAGE_KEY = 'tph_delivery_draft';
    const AGENCIES = ['ZOOM', 'MRW', 'TEALCA', 'Domesa'];
    const DOC_TYPES = ['V', 'E', 'J', 'G', 'P'];
    const SMALL_WORDS = new Set(['de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'en', 'al', 'a']);
    const PRESERVE_UPPER = new Set(['ZOOM', 'MRW', 'TEALCA', 'CC', 'C.C.', 'AV', 'URB', 'EDIF', 'RIF', 'PB', 'MZ', 'KM']);

    const STATES_VE = [
        'Amazonas', 'Anzoátegui', 'Apure', 'Aragua', 'Barinas', 'Bolívar',
        'Carabobo', 'Cojedes', 'Delta Amacuro', 'Distrito Capital', 'Falcón',
        'Guárico', 'La Guaira', 'Lara', 'Mérida', 'Miranda', 'Monagas',
        'Nueva Esparta', 'Portuguesa', 'Sucre', 'Táchira', 'Trujillo',
        'Yaracuy', 'Zulia'
    ];

    const CITIES_BY_STATE = {
        'Amazonas': ['Puerto Ayacucho', 'San Fernando de Atabapo'],
        'Anzoátegui': ['Barcelona', 'Puerto La Cruz', 'Lechería', 'Guanta', 'El Tigre', 'Anaco', 'Cantaura'],
        'Apure': ['San Fernando de Apure', 'Guasdualito', 'Achaguas', 'Biruaca'],
        'Aragua': ['Maracay', 'Turmero', 'Cagua', 'La Victoria', 'El Limón', 'Palo Negro', 'Villa de Cura'],
        'Barinas': ['Barinas', 'Barinitas', 'Socopó', 'Santa Bárbara de Barinas'],
        'Bolívar': ['Puerto Ordaz', 'San Félix', 'Ciudad Guayana', 'Ciudad Bolívar', 'Upata', 'Santa Elena de Uairén'],
        'Carabobo': ['Valencia', 'Naguanagua', 'San Diego', 'Puerto Cabello', 'Guacara', 'Tocuyito', 'Los Guayos'],
        'Cojedes': ['San Carlos', 'Tinaquillo', 'Tinaco'],
        'Delta Amacuro': ['Tucupita', 'Sierra Imataca'],
        'Distrito Capital': ['Caracas', 'El Paraíso', 'Catia', 'Chacao', 'La Urbina', 'Petare', 'Boleíta'],
        'Falcón': ['Coro', 'Punto Fijo', 'Judibana', 'Tucacas', 'Dabajuro'],
        'Guárico': ['San Juan de los Morros', 'Calabozo', 'Valle de la Pascua', 'Zaraza', 'Altagracia de Orituco'],
        'La Guaira': ['La Guaira', 'Maiquetía', 'Catia La Mar', 'Caraballeda', 'Macuto'],
        'Lara': ['Barquisimeto', 'Cabudare', 'Carora', 'El Tocuyo', 'Quíbor'],
        'Mérida': ['Mérida', 'Ejido', 'El Vigía', 'Tovar'],
        'Miranda': ['Chacao', 'Baruta', 'El Hatillo', 'Petare', 'Los Teques', 'Guarenas', 'Guatire', 'Charallave', 'Cúa', 'San Antonio de los Altos', 'Higuerote'],
        'Monagas': ['Maturín', 'Punta de Mata', 'Caripito', 'Temblador'],
        'Nueva Esparta': ['Porlamar', 'Pampatar', 'Juan Griego', 'La Asunción', 'El Valle del Espíritu Santo'],
        'Portuguesa': ['Acarigua', 'Araure', 'Guanare', 'Turén'],
        'Sucre': ['Cumaná', 'Carúpano', 'Güiria', 'Cumanacoa'],
        'Táchira': ['San Cristóbal', 'Táriba', 'San Antonio del Táchira', 'Rubio', 'La Fría', 'Ureña'],
        'Trujillo': ['Valera', 'Trujillo', 'Boconó', 'Sabana de Mendoza'],
        'Yaracuy': ['San Felipe', 'Yaritagua', 'Chivacoa', 'Nirgua'],
        'Zulia': ['Maracaibo', 'San Francisco', 'Cabimas', 'Ciudad Ojeda', 'Machiques', 'Santa Bárbara del Zulia']
    };

    const instances = new Map();
    let leafletPromise = null;
    let stylesInjected = false;

    function getZonesData() {
        const raw = global.__DELIVERY_ZONES__ || {};
        return {
            rate_bs: Number(raw.rate_bs || 0),
            center: Array.isArray(raw.center) && raw.center.length === 2 ? raw.center : [10.4882, -66.8240],
            zones: Array.isArray(raw.zones) ? raw.zones : []
        };
    }

    function formatBs(amount) {
        if (amount == null || isNaN(amount)) return 'Bs. 0,00';
        return 'Bs. ' + Number(amount).toLocaleString('es-VE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function esc(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function displayZoneName(name) {
        const clean = String(name || '').trim();
        if (!clean) return 'Zona Delivery';
        return clean.charAt(0).toUpperCase() + clean.slice(1);
    }

    function cleanSpaces(val) {
        return String(val || '').replace(/\s+/g, ' ').trim();
    }

    function normalizeTitleCase(text) {
        const cleaned = cleanSpaces(text);
        if (!cleaned) return '';
        const words = cleaned.split(' ');
        return words.map((word, idx) => {
            const plain = word.replace(/[.,;:()]/g, '').toUpperCase();
            if (PRESERVE_UPPER.has(plain)) return word.toUpperCase();
            const lower = word.toLowerCase();
            if (idx > 0 && idx < words.length - 1 && SMALL_WORDS.has(lower)) {
                return lower;
            }
            return lower.charAt(0).toUpperCase() + lower.slice(1);
        }).join(' ');
    }

    function normalizePhone(raw) {
        let digits = String(raw || '').replace(/[^\d]/g, '');
        if (digits.startsWith('58') && digits.length >= 12) {
            digits = '0' + digits.slice(2);
        } else if (digits.length === 10 && digits.startsWith('4')) {
            digits = '0' + digits;
        }
        return digits;
    }

    function normalizeCedula(docType, docNum) {
        const prefix = DOC_TYPES.includes(String(docType || '').toUpperCase())
            ? String(docType).toUpperCase()
            : 'V';
        const digits = String(docNum || '').replace(/[^\d]/g, '');
        if (!digits) return '';
        return `${prefix}-${digits}`;
    }

    function normalizeOfficeString(oficinaRaw, agency, estado, ciudad) {
        let text = cleanSpaces(oficinaRaw);
        if (!text) return '';
        const originalText = text;
        const escRe = (s) => String(s || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        if (agency) {
            text = text.replace(new RegExp(`^(?:agencia\\s+)?${escRe(agency)}\\b[\\s\\-,:]*`, 'i'), '');
            text = text.replace(new RegExp(`\\b${escRe(agency)}\\b`, 'ig'), '');
        }
        const beforeGeoStrip = cleanSpaces(text.replace(/^[\s,\-]+|[\s,\-]+$/g, ''));
        if (estado) {
            text = text.replace(new RegExp(`[\\s,\\-]*(?:edo\\.?|estado)\\s+${escRe(estado)}\\b`, 'ig'), '');
            text = text.replace(new RegExp(`[\\s,\\-]+${escRe(estado)}\\s*$`, 'i'), '');
        }
        if (ciudad) {
            text = text.replace(new RegExp(`[\\s,\\-]+${escRe(ciudad)}\\s*$`, 'i'), '');
        }
        text = cleanSpaces(text.replace(/^[\s,\-]+|[\s,\-]+$/g, ''));
        if (!text) text = beforeGeoStrip || originalText;
        return normalizeTitleCase(text);
    }

    function normalizeShippingData(s) {
        const agencia = AGENCIES.includes(s.agencia) ? s.agencia : 'ZOOM';
        const estado = STATES_VE.includes(s.estado) ? s.estado : cleanSpaces(s.estado);
        const ciudad = normalizeTitleCase(String(s.ciudad || '').replace(/^(?:ciudad\s+de\s+)/i, ''));
        const nombre = normalizeTitleCase(s.nombre);
        const cedula = normalizeCedula(s.docType, s.docNum);
        const telefono = normalizePhone(s.telefono);
        const correo = cleanSpaces(s.correo).toLowerCase();
        const oficinaClean = normalizeOfficeString(s.oficina, agencia, estado, ciudad);

        const parts = [];
        if (ciudad && estado) parts.push(`${ciudad}, Edo. ${estado}`);
        else if (estado) parts.push(`Edo. ${estado}`);
        else if (ciudad) parts.push(ciudad);
        if (oficinaClean) parts.push(oficinaClean);

        const oficinaCompleta = parts.length > 0
            ? `${agencia} - ${parts.join(' - ')}`
            : agencia;

        return {
            nombre,
            cedula,
            telefono,
            correo,
            agencia,
            estado,
            ciudad,
            oficinaClean,
            oficinaCompleta
        };
    }

    // Ray-casting Point-in-Polygon (parity with mostrador.html & ZapStore)
    function pointInRing(lat, lng, ring) {
        if (!Array.isArray(ring) || ring.length < 3) return false;
        let inside = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            const xi = Number(ring[i][1]); // lat
            const yi = Number(ring[i][0]); // lng
            const xj = Number(ring[j][1]);
            const yj = Number(ring[j][0]);
            const intersect = ((yi > lng) !== (yj > lng)) &&
                (lat < ((xj - xi) * (lng - yi)) / ((yj - yi) || 1e-12) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    function pointInPolygonRings(lat, lng, rings) {
        if (!Array.isArray(rings) || rings.length === 0) return false;
        if (!pointInRing(lat, lng, rings[0])) return false;
        for (let h = 1; h < rings.length; h++) {
            if (pointInRing(lat, lng, rings[h])) return false;
        }
        return true;
    }

    function pointInGeoJSON(lat, lng, geo) {
        if (!geo) return false;
        const geom = geo.type === 'Feature' ? geo.geometry : geo;
        if (!geom || !geom.coordinates) return false;
        if (geom.type === 'Polygon') {
            return pointInPolygonRings(lat, lng, geom.coordinates);
        }
        if (geom.type === 'MultiPolygon') {
            return geom.coordinates.some((poly) => pointInPolygonRings(lat, lng, poly));
        }
        return false;
    }

    function findMatchingZone(lat, lng) {
        const data = getZonesData();
        const matches = [];
        for (const z of data.zones) {
            if (pointInGeoJSON(lat, lng, z.geojson)) {
                matches.push(z);
            }
        }
        if (matches.length === 0) return null;
        matches.sort((a, b) => {
            const pa = Number(a.precio_usd || a.precio_bs || 0);
            const pb = Number(b.precio_usd || b.precio_bs || 0);
            if (pa !== pb) return pa - pb;
            return Number(a.id || 0) - Number(b.id || 0);
        });
        return matches[0];
    }

    function loadDraftShipping() {
        const base = {
            nombre: '',
            docType: 'V',
            docNum: '',
            telefono: '',
            correo: '',
            agencia: 'ZOOM',
            estado: '',
            ciudad: '',
            oficina: ''
        };
        try {
            const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
            if (!raw) return base;
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') return base;
            return {
                nombre: String(parsed.nombre || ''),
                docType: DOC_TYPES.includes(parsed.docType) ? parsed.docType : 'V',
                docNum: String(parsed.docNum || ''),
                telefono: String(parsed.telefono || ''),
                correo: String(parsed.correo || ''),
                agencia: AGENCIES.includes(parsed.agencia) ? parsed.agencia : 'ZOOM',
                estado: STATES_VE.includes(parsed.estado) ? parsed.estado : '',
                ciudad: String(parsed.ciudad || ''),
                oficina: String(parsed.oficina || '')
            };
        } catch (e) {
            return base;
        }
    }

    function saveDraftShipping(shipping) {
        try {
            localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(shipping));
        } catch (e) {}
    }

    function injectStyles() {
        if (stylesInjected || document.getElementById('tph-delivery-styles')) {
            stylesInjected = true;
            return;
        }
        stylesInjected = true;
        const css = `
.tph-del-wrap{width:100%;margin:4px 0 8px;font-family:'Outfit',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
.tph-del-trigger{width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:11px 14px;border-radius:12px;border:1px solid rgba(255,106,0,0.38);background:rgba(255,106,0,0.08);color:#f3f4f6;font-size:13.5px;font-weight:700;cursor:pointer;transition:background .2s,border-color .2s,transform .15s;font-family:inherit;text-align:left;}
.tph-del-trigger:hover{background:rgba(255,106,0,0.14);border-color:rgba(255,106,0,0.65);}
.tph-del-trigger.has-selection{background:rgba(37,211,102,0.1);border-color:rgba(37,211,102,0.45);}
.tph-del-trig-main{display:flex;align-items:center;gap:8px;min-width:0;}
.tph-del-trig-main svg{width:17px;height:17px;fill:#ff6a00;flex-shrink:0;}
.tph-del-trigger.has-selection .tph-del-trig-main svg{fill:#25d366;}
.tph-del-trig-main span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tph-del-trig-right{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.tph-del-trig-tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;background:rgba(255,255,255,0.08);color:#c0c2d0;font-variant-numeric:tabular-nums;max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tph-del-trigger.has-selection .tph-del-trig-tag{background:rgba(37,211,102,0.18);color:#6ee7a8;}
.tph-del-chev{width:16px;height:16px;fill:#c0c2d0;transition:transform .2s;flex-shrink:0;}
.tph-del-trigger[aria-expanded="true"] .tph-del-chev{transform:rotate(180deg);}
.tph-del-body{margin-top:8px;padding:12px;border-radius:14px;background:#13131a;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;gap:10px;}
.tph-del-body[hidden]{display:none;}
.tph-del-tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.tph-del-tab{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;padding:10px 8px;border-radius:11px;border:1px solid rgba(255,255,255,0.12);background:#1b1b24;color:#e5e7eb;cursor:pointer;font-family:inherit;transition:all .18s;}
.tph-del-tab:hover{border-color:rgba(255,106,0,0.55);background:#22222d;}
.tph-del-tab.active{border-color:#ff6a00;background:rgba(255,106,0,0.16);color:#ffffff;box-shadow:0 0 0 1px rgba(255,106,0,0.35);}
.tph-del-tab-head{display:flex;align-items:center;gap:6px;font-size:13.5px;font-weight:800;}
.tph-del-tab-head svg{width:16px;height:16px;fill:#ff6a00;flex-shrink:0;}
.tph-del-tab small{font-size:10.5px;color:#9ca3af;font-weight:500;line-height:1.2;text-align:center;}
.tph-del-panel{display:flex;flex-direction:column;gap:10px;}
.tph-del-panel[hidden]{display:none;}
.tph-del-gps-btn{width:100%;display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,106,0,0.6);background:#ff6a00;color:#ffffff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:background .18s,transform .12s;}
.tph-del-gps-btn:hover:not(:disabled){background:#f05a18;}
.tph-del-gps-btn:disabled{opacity:0.75;cursor:wait;}
.tph-del-gps-btn svg{width:17px;height:17px;fill:currentColor;flex-shrink:0;}
.tph-del-map-wrap{position:relative;width:100%;height:200px;border-radius:11px;overflow:hidden;border:1px solid rgba(255,255,255,0.14);background:#0c0d12;}
.tph-del-map-canvas{width:100%;height:100%;z-index:1;}
.tph-del-map-recenter{position:absolute;top:8px;right:8px;z-index:500;width:34px;height:34px;border-radius:8px;border:1px solid rgba(255,255,255,0.2);background:rgba(15,15,22,0.9);color:#ff6a00;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,0.45);}
.tph-del-map-recenter:hover{background:#ff6a00;color:#fff;}
.tph-del-map-recenter svg{width:18px;height:18px;fill:currentColor;}
.tph-del-map-hint{font-size:11.5px;color:#9ca3af;line-height:1.35;}
.tph-map-pin{background:transparent;border:none;}
.tph-map-pin-inner{width:28px;height:36px;display:flex;align-items:center;justify-content:center;filter:drop-shadow(0 3px 6px rgba(0,0,0,0.65));cursor:grab;}
.tph-del-status{padding:10px 12px;border-radius:10px;font-size:12.5px;line-height:1.45;display:flex;flex-direction:column;gap:6px;}
.tph-del-status.ok{background:rgba(37,211,102,0.1);border:1px solid rgba(37,211,102,0.35);color:#d1fae5;}
.tph-del-status.warn{background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.4);color:#fde68a;}
.tph-del-status.err{background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.42);color:#fecaca;}
.tph-del-status.idle{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);color:#c0c2d0;}
.tph-del-zone-row{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:700;}
.tph-del-zone-price{color:#6ee7a8;font-size:15px;font-weight:800;font-variant-numeric:tabular-nums;}
.tph-del-switch-btn{align-self:flex-start;padding:7px 12px;border-radius:8px;border:none;background:#ff6a00;color:#fff;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;}
.tph-del-switch-btn:hover{background:#f05a18;}
.tph-del-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.tph-del-field{display:flex;flex-direction:column;gap:4px;}
.tph-del-field.full{grid-column:1 / -1;}
.tph-del-label{font-size:11.5px;font-weight:700;color:#c0c2d0;}
.tph-del-req{color:#ff6a00;}
.tph-del-input,.tph-del-select{width:100%;box-sizing:border-box;padding:9px 10px;border-radius:9px;border:1px solid rgba(255,255,255,0.14);background:#0c0d12;color:#ffffff;font-size:13.5px;font-family:inherit;outline:none;transition:border-color .15s;}
.tph-del-input:focus,.tph-del-select:focus{border-color:#ff6a00;}
.tph-del-doc-row{display:flex;gap:6px;}
.tph-del-doc-type{width:64px;flex-shrink:0;}
.tph-del-preview{padding:8px 10px;border-radius:9px;background:rgba(255,106,0,0.07);border:1px dashed rgba(255,106,0,0.35);font-size:11.5px;color:#e5e7eb;line-height:1.4;}
.tph-del-preview strong{color:#ffa24d;}
.tph-del-error-msg{padding:8px 10px;border-radius:8px;background:rgba(239,68,68,0.14);border:1px solid rgba(239,68,68,0.45);color:#fecaca;font-size:12px;font-weight:600;}
.tph-del-error-msg[hidden]{display:none;}
.tph-del-foot-bar{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:2px;}
.tph-del-clear-btn{background:transparent;border:none;color:#9ca3af;font-size:11.5px;cursor:pointer;text-decoration:underline;padding:2px 0;font-family:inherit;}
.tph-del-clear-btn:hover{color:#ffffff;}
.cart-footer.tph-drawer-expanded{max-height:calc(100% - 135px);overflow-y:auto;overscroll-behavior:contain;gap:10px;padding:14px 18px;background:#0d0e14;}
@media (max-width:600px){
  .tph-del-trigger{padding:10px 11px;font-size:12.5px;gap:6px;}
  .tph-del-trig-tag{max-width:175px;font-size:10.5px;padding:2px 7px;}
  .tph-del-form-grid{grid-template-columns:1fr;}
  .tph-del-input,.tph-del-select{font-size:16px;padding:10px;}
  .tph-del-map-wrap{height:185px;}
  .cart-footer.tph-drawer-expanded{max-height:calc(100% - 120px);padding:12px 14px;}
}`;
        const styleEl = document.createElement('style');
        styleEl.id = 'tph-delivery-styles';
        styleEl.textContent = css;
        document.head.appendChild(styleEl);
    }

    function ensureLeafletLoaded(basePath) {
        if (global.L && typeof global.L.map === 'function') {
            return Promise.resolve(global.L);
        }
        if (leafletPromise) return leafletPromise;
        const prefix = basePath || './';
        leafletPromise = new Promise((resolve, reject) => {
            if (!document.getElementById('tph-leaflet-css')) {
                const link = document.createElement('link');
                link.id = 'tph-leaflet-css';
                link.rel = 'stylesheet';
                link.href = `${prefix}assets/leaflet/leaflet.min.css`;
                document.head.appendChild(link);
            }
            const existingScript = document.getElementById('tph-leaflet-js');
            if (existingScript) {
                existingScript.addEventListener('load', () => resolve(global.L));
                existingScript.addEventListener('error', reject);
                return;
            }
            const script = document.createElement('script');
            script.id = 'tph-leaflet-js';
            script.src = `${prefix}assets/leaflet/leaflet.min.js`;
            script.async = true;
            script.onload = () => {
                if (global.L) resolve(global.L);
                else reject(new Error('Leaflet no pudo inicializar'));
            };
            script.onerror = () => reject(new Error('Error cargando Leaflet local'));
            document.head.appendChild(script);
        });
        return leafletPromise;
    }

    function createDefaultState(context) {
        return {
            context,
            isExpanded: false,
            mode: null, // null | 'delivery' | 'shipping'
            gpsLat: null,
            gpsLng: null,
            gpsAccuracy: null,
            zone: null,
            outOfZone: false,
            gpsStatus: 'idle',
            gpsError: '',
            reference: '',
            shipping: loadDraftShipping(),
            validationError: '',
            map: null,
            marker: null,
            mapInitialized: false,
            containerEl: null,
            options: {}
        };
    }

    function syncDrawerClass(inst) {
        if (!inst.containerEl) return;
        const footer = inst.containerEl.closest('.cart-footer');
        if (footer) {
            footer.classList.toggle('tph-drawer-expanded', Boolean(inst.isExpanded));
        }
    }

    function notifyChange(inst) {
        updateTriggerSummary(inst);
        if (typeof inst.options.onChange === 'function') {
            try {
                inst.options.onChange(getPublicState(inst));
            } catch (e) {}
        }
    }

    function updateTriggerSummary(inst) {
        if (!inst.containerEl) return;
        const trigger = inst.containerEl.querySelector('.tph-del-trigger');
        const tag = inst.containerEl.querySelector('.tph-del-trig-tag');
        const body = inst.containerEl.querySelector('.tph-del-body');
        if (!trigger || !tag || !body) return;

        trigger.setAttribute('aria-expanded', inst.isExpanded ? 'true' : 'false');
        body.hidden = !inst.isExpanded;
        syncDrawerClass(inst);

        const tabs = inst.containerEl.querySelectorAll('.tph-del-tab');
        tabs.forEach((btn) => {
            const active = btn.getAttribute('data-mode') === inst.mode;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });

        const delPanel = inst.containerEl.querySelector('.tph-del-panel-delivery');
        const shipPanel = inst.containerEl.querySelector('.tph-del-panel-shipping');
        if (delPanel) delPanel.hidden = inst.mode !== 'delivery';
        if (shipPanel) shipPanel.hidden = inst.mode !== 'shipping';

        let hasSel = false;
        let tagText = 'Opcional';
        let labelText = '¿Quieres delivery o envío?';
        if (inst.mode === 'delivery') {
            labelText = 'Entrega: Delivery';
            if (inst.zone) {
                hasSel = true;
                tagText = `${displayZoneName(inst.zone.nombre)} · ${formatBs(inst.zone.precio_bs)}`;
            } else if (inst.outOfZone) {
                tagText = 'Fuera de zona';
            } else {
                tagText = 'Ubicar GPS';
            }
        } else if (inst.mode === 'shipping') {
            hasSel = true;
            labelText = 'Entrega: Envío';
            const norm = normalizeShippingData(inst.shipping);
            tagText = norm.estado ? `${norm.agencia} · ${norm.estado}` : norm.agencia;
        }

        const labelSpan = trigger.querySelector('.tph-del-trig-main span');
        if (labelSpan) labelSpan.textContent = labelText;
        trigger.classList.toggle('has-selection', hasSel);
        tag.textContent = tagText;
    }

    function renderDeliveryStatus(inst) {
        if (!inst.containerEl) return;
        const box = inst.containerEl.querySelector('.tph-del-status');
        if (!box) return;

        if (inst.gpsStatus === 'ready' && inst.zone) {
            box.className = 'tph-del-status ok';
            box.innerHTML = `
                <div class="tph-del-zone-row">
                    <span>Zona detectada: <strong>${esc(displayZoneName(inst.zone.nombre))}</strong></span>
                    <span class="tph-del-zone-price">${esc(formatBs(inst.zone.precio_bs))}</span>
                </div>
                <div style="font-size:11px;opacity:0.88;">
                    Pin fijado: ${inst.gpsLat.toFixed(5)}, ${inst.gpsLng.toFixed(5)} · Tarifa actualizada en Bs.
                </div>
            `;
            return;
        }

        if (inst.outOfZone && inst.gpsLat != null) {
            box.className = 'tph-del-status warn';
            box.innerHTML = `
                <div><strong>Ubicación fuera del área de delivery directo.</strong> Puedes mover el pin dentro de Caracas / Guarenas / Guatire o cambiar a Envío Nacional cobro en destino.</div>
                <button type="button" class="tph-del-switch-btn" data-action="switch-shipping">Cambiar a Envío Nacional</button>
            `;
            const swBtn = box.querySelector('[data-action="switch-shipping"]');
            if (swBtn) {
                swBtn.addEventListener('click', () => setMode(inst, 'shipping'));
            }
            return;
        }

        if (inst.gpsStatus === 'denied' || inst.gpsStatus === 'error') {
            box.className = 'tph-del-status err';
            box.textContent = inst.gpsError || 'No pudimos obtener tu ubicación automática. Toca o arrastra el pin directamente en el mapa.';
            return;
        }

        box.className = 'tph-del-status idle';
        box.textContent = 'Presiona "Usar mi ubicación actual" o toca directamente el mapa para calcular tu tarifa en Bs.';
    }

    function renderErrorBanner(inst) {
        if (!inst.containerEl) return;
        const errEl = inst.containerEl.querySelector('.tph-del-error-msg');
        if (!errEl) return;
        if (inst.validationError) {
            errEl.textContent = inst.validationError;
            errEl.hidden = false;
        } else {
            errEl.textContent = '';
            errEl.hidden = true;
        }
    }

    function evaluateCoordinates(inst, lat, lng, centerMap) {
        inst.gpsLat = Number(lat);
        inst.gpsLng = Number(lng);
        inst.validationError = '';

        const matched = findMatchingZone(inst.gpsLat, inst.gpsLng);
        if (matched) {
            inst.zone = {
                id: matched.id,
                nombre: matched.nombre,
                precio_usd: matched.precio_usd,
                precio_bs: matched.precio_bs
            };
            inst.outOfZone = false;
            inst.gpsStatus = 'ready';
            inst.gpsError = '';
        } else {
            inst.zone = null;
            inst.outOfZone = true;
            inst.gpsStatus = 'out_of_zone';
            inst.gpsError = '';
        }

        updateMarkerOnMap(inst, inst.gpsLat, inst.gpsLng, centerMap);
        renderDeliveryStatus(inst);
        renderErrorBanner(inst);
        notifyChange(inst);
    }

    function updateMarkerOnMap(inst, lat, lng, centerMap) {
        if (!inst.map || !global.L) return;
        const L = global.L;
        if (!inst.marker) {
            const pinIcon = L.divIcon({
                className: 'tph-map-pin',
                iconSize: [28, 36],
                iconAnchor: [14, 36],
                html: `<div class="tph-map-pin-inner"><svg viewBox="0 0 24 30" width="28" height="36"><path d="M12 0C5.37 0 0 5.37 0 12c0 8.5 12 18 12 18s12-9.5 12-18C24 5.37 18.63 0 12 0z" fill="#ff6a00" stroke="#ffffff" stroke-width="2"/><circle cx="12" cy="11.5" r="4.5" fill="#ffffff"/></svg></div>`
            });
            inst.marker = L.marker([lat, lng], { draggable: true, icon: pinIcon }).addTo(inst.map);
            inst.marker.on('dragend', () => {
                const pos = inst.marker.getLatLng();
                evaluateCoordinates(inst, pos.lat, pos.lng, false);
            });
        } else {
            inst.marker.setLatLng([lat, lng]);
        }
        if (centerMap) {
            inst.map.setView([lat, lng], Math.max(inst.map.getZoom() || 13, 15));
        }
    }

    function initMapIfNeeded(inst) {
        if (!inst.containerEl) return;
        const mapEl = inst.containerEl.querySelector('.tph-del-map-canvas');
        if (!mapEl) return;

        ensureLeafletLoaded(inst.options.basePath).then((L) => {
            if (!inst.map) {
                const center = getZonesData().center;
                inst.map = L.map(mapEl, { zoomControl: true, attributionControl: true }).setView(center, 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '&copy; OSM'
                }).addTo(inst.map);

                // Solo mapa y pin arrastrable: nunca renderizar polígonos de zonas
                inst.map.on('click', (e) => {
                    evaluateCoordinates(inst, e.latlng.lat, e.latlng.lng, false);
                });
                inst.mapInitialized = true;

                if (inst.gpsLat != null && inst.gpsLng != null) {
                    updateMarkerOnMap(inst, inst.gpsLat, inst.gpsLng, true);
                }
            }
            setTimeout(() => {
                if (inst.map) inst.map.invalidateSize();
            }, 180);
        }).catch(() => {
            inst.gpsStatus = 'error';
            inst.gpsError = 'No se pudo cargar el mapa interactivo en este momento. Intenta usar tu ubicación GPS actual.';
            renderDeliveryStatus(inst);
        });
    }

    function locateGPS(inst) {
        const gpsBtn = inst.containerEl ? inst.containerEl.querySelector('.tph-del-gps-btn') : null;
        if (!navigator.geolocation) {
            inst.gpsStatus = 'error';
            inst.gpsError = 'Tu navegador no soporta geolocalización GPS. Toca o arrastra el pin directamente en el mapa.';
            renderDeliveryStatus(inst);
            return;
        }

        const origHtml = gpsBtn ? gpsBtn.innerHTML : '';
        if (gpsBtn) {
            gpsBtn.disabled = true;
            gpsBtn.innerHTML = '<span>Detectando ubicación GPS...</span>';
        }
        inst.validationError = '';
        renderErrorBanner(inst);

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                if (gpsBtn) {
                    gpsBtn.disabled = false;
                    gpsBtn.innerHTML = origHtml;
                }
                inst.gpsAccuracy = pos.coords.accuracy || null;
                evaluateCoordinates(inst, pos.coords.latitude, pos.coords.longitude, true);
            },
            (err) => {
                if (gpsBtn) {
                    gpsBtn.disabled = false;
                    gpsBtn.innerHTML = origHtml;
                }
                if (err && err.code === 1) {
                    inst.gpsStatus = 'denied';
                    inst.gpsError = 'Permiso de ubicación denegado. Activa el GPS para tu navegador o marca tu punto directamente en el mapa.';
                } else {
                    inst.gpsStatus = 'error';
                    inst.gpsError = 'No pudimos obtener tu señal GPS (tiempo agotado). Toca o arrastra el pin directamente en el mapa.';
                }
                renderDeliveryStatus(inst);
            },
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
        );
    }

    function updateCityDatalist(inst) {
        if (!inst.containerEl) return;
        const dl = inst.containerEl.querySelector(`#tph-cities-${inst.context}`);
        if (!dl) return;
        const cities = CITIES_BY_STATE[inst.shipping.estado] || [];
        dl.innerHTML = cities.map((c) => `<option value="${esc(c)}"></option>`).join('');
    }

    function updateShippingPreview(inst) {
        if (!inst.containerEl) return;
        const prev = inst.containerEl.querySelector('.tph-del-preview');
        if (!prev) return;
        const norm = normalizeShippingData(inst.shipping);
        const lines = [];
        if (norm.nombre) lines.push(`${esc(norm.nombre)}${norm.cedula ? ' (' + esc(norm.cedula) + ')' : ''}`);
        lines.push(`<strong>${esc(norm.oficinaCompleta)}</strong>`);
        prev.innerHTML = `Vista previa despacho: ${lines.join(' · ')}`;
    }

    function setMode(inst, nextMode) {
        inst.isExpanded = true;
        inst.mode = inst.mode === nextMode ? nextMode : nextMode;
        inst.validationError = '';
        renderErrorBanner(inst);
        updateTriggerSummary(inst);

        if (inst.mode === 'delivery') {
            initMapIfNeeded(inst);
            renderDeliveryStatus(inst);
        } else if (inst.mode === 'shipping') {
            updateCityDatalist(inst);
            updateShippingPreview(inst);
        }

        const panel = inst.containerEl ? inst.containerEl.querySelector('.tph-del-body') : null;
        if (panel) {
            setTimeout(() => {
                try { panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) {}
            }, 60);
        }
        notifyChange(inst);
    }

    function clearSelection(inst) {
        inst.mode = null;
        inst.isExpanded = false;
        inst.validationError = '';
        renderErrorBanner(inst);
        updateTriggerSummary(inst);
        notifyChange(inst);
    }

    function bindShippingInputs(inst) {
        const root = inst.containerEl;
        if (!root) return;

        const syncShipping = () => {
            saveDraftShipping(inst.shipping);
            updateShippingPreview(inst);
            inst.validationError = '';
            renderErrorBanner(inst);
            notifyChange(inst);
        };

        const bindVal = (sel, key, onChangeExtra) => {
            const el = root.querySelector(sel);
            if (!el) return;
            el.value = inst.shipping[key] || '';
            el.addEventListener('input', () => {
                inst.shipping[key] = el.value;
                if (onChangeExtra) onChangeExtra(el);
                syncShipping();
            });
            el.addEventListener('change', () => {
                inst.shipping[key] = el.value;
                if (onChangeExtra) onChangeExtra(el);
                syncShipping();
            });
        };

        bindVal('[data-ship="nombre"]', 'nombre');
        bindVal('[data-ship="docType"]', 'docType');
        bindVal('[data-ship="docNum"]', 'docNum', (el) => {
            // Si el usuario pega "V-27123456", extraer la letra y limpiar solo dígitos
            const raw = el.value.trim().toUpperCase();
            const prefixMatch = raw.match(/^([VEJGP])[\s\-]*/);
            if (prefixMatch) {
                inst.shipping.docType = prefixMatch[1];
                const dt = root.querySelector('[data-ship="docType"]');
                if (dt) dt.value = prefixMatch[1];
            }
            const cleanDigits = raw.replace(/[^\d]/g, '');
            inst.shipping.docNum = cleanDigits;
            el.value = cleanDigits;
        });
        bindVal('[data-ship="telefono"]', 'telefono', (el) => {
            el.value = el.value.replace(/[^\d+\s\-]/g, '');
            inst.shipping.telefono = el.value;
        });
        bindVal('[data-ship="correo"]', 'correo');
        bindVal('[data-ship="agencia"]', 'agencia');
        bindVal('[data-ship="estado"]', 'estado', () => {
            updateCityDatalist(inst);
        });
        bindVal('[data-ship="ciudad"]', 'ciudad');
        bindVal('[data-ship="oficina"]', 'oficina');

        // Normalizar visualmente al salir del campo
        const blurNormalize = (sel, key, fn) => {
            const el = root.querySelector(sel);
            if (!el) return;
            el.addEventListener('blur', () => {
                const v = fn(el.value);
                el.value = v;
                inst.shipping[key] = v;
                syncShipping();
            });
        };
        blurNormalize('[data-ship="nombre"]', 'nombre', normalizeTitleCase);
        blurNormalize('[data-ship="ciudad"]', 'ciudad', normalizeTitleCase);
        blurNormalize('[data-ship="telefono"]', 'telefono', normalizePhone);
        blurNormalize('[data-ship="oficina"]', 'oficina', (val) =>
            normalizeOfficeString(val, inst.shipping.agencia, inst.shipping.estado, inst.shipping.ciudad) || cleanSpaces(val)
        );
    }

    function renderMarkup(inst) {
        const ctx = inst.context;
        const statesOpts = ['<option value="">Selecciona un estado...</option>']
            .concat(STATES_VE.map((st) => `<option value="${esc(st)}">${esc(st)}</option>`))
            .join('');
        const docOpts = DOC_TYPES.map((d) => `<option value="${d}">${d}</option>`).join('');
        const agOpts = AGENCIES.map((a) => `<option value="${a}">${a}</option>`).join('');

        inst.containerEl.innerHTML = `
        <div class="tph-del-wrap" data-ctx="${esc(ctx)}">
            <button type="button" class="tph-del-trigger" aria-expanded="false">
                <span class="tph-del-trig-main">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.66 1.34 3 3 3s3-1.34 3-3h6c0 1.66 1.34 3 3 3s3-1.34 3-3h2v-5l-3-4zM6 18.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm13.5-9l1.96 2.5H17V9.5h2.5zm-1.5 9c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
                    <span>¿Quieres delivery o envío?</span>
                </span>
                <span class="tph-del-trig-right">
                    <span class="tph-del-trig-tag">Opcional</span>
                    <svg class="tph-del-chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
                </span>
            </button>
            <div class="tph-del-body" hidden>
                <div class="tph-del-tabs" role="group" aria-label="Selecciona modalidad de entrega">
                    <button type="button" class="tph-del-tab" data-mode="delivery" aria-pressed="false">
                        <span class="tph-del-tab-head">
                            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                            <span>Delivery</span>
                        </span>
                        <small>Caracas / Guarenas / Guatire</small>
                    </button>
                    <button type="button" class="tph-del-tab" data-mode="shipping" aria-pressed="false">
                        <span class="tph-del-tab-head">
                            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                            <span>Envío</span>
                        </span>
                        <small>ZOOM · MRW · TEALCA · Domesa</small>
                    </button>
                </div>

                <div class="tph-del-panel tph-del-panel-delivery" hidden>
                    <button type="button" class="tph-del-gps-btn">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0 0 13 3.06V1h-2v2.06A8.994 8.994 0 0 0 3.06 11H1v2h2.06A8.994 8.994 0 0 0 11 20.94V23h2v-2.06A8.994 8.994 0 0 0 20.94 13H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>
                        <span>Usar mi ubicación actual</span>
                    </button>
                    <div class="tph-del-map-wrap">
                        <div class="tph-del-map-canvas"></div>
                        <button type="button" class="tph-del-map-recenter" title="Usar mi ubicación GPS actual" aria-label="Centrar en mi ubicación GPS">
                            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0 0 13 3.06V1h-2v2.06A8.994 8.994 0 0 0 3.06 11H1v2h2.06A8.994 8.994 0 0 0 11 20.94V23h2v-2.06A8.994 8.994 0 0 0 20.94 13H23v-2h-2.06z"/></svg>
                        </button>
                    </div>
                    <div class="tph-del-map-hint">Toca o arrastra el pin en el mapa al punto exacto de entrega.</div>
                    <div class="tph-del-status idle">Presiona "Usar mi ubicación actual" o toca directamente el mapa para calcular tu tarifa en Bs.</div>
                    <div class="tph-del-field full">
                        <label class="tph-del-label" for="tph-ref-${esc(ctx)}">Punto de referencia / Edificio (opcional)</label>
                        <input id="tph-ref-${esc(ctx)}" type="text" maxlength="120" class="tph-del-input tph-del-ref-input" placeholder="Ej: Edif. Roraima, Piso 2, Portón negro">
                    </div>
                </div>

                <div class="tph-del-panel tph-del-panel-shipping" hidden>
                    <div class="tph-del-form-grid">
                        <div class="tph-del-field full">
                            <label class="tph-del-label" for="tph-nom-${esc(ctx)}">Nombre de quien recibe <span class="tph-del-req">*</span></label>
                            <input id="tph-nom-${esc(ctx)}" data-ship="nombre" type="text" maxlength="90" class="tph-del-input" placeholder="Ej: Carlos Pérez">
                        </div>
                        <div class="tph-del-field">
                            <label class="tph-del-label" for="tph-doc-${esc(ctx)}">Cédula o RIF <span class="tph-del-req">*</span></label>
                            <div class="tph-del-doc-row">
                                <select data-ship="docType" aria-label="Tipo de documento" class="tph-del-select tph-del-doc-type">${docOpts}</select>
                                <input id="tph-doc-${esc(ctx)}" data-ship="docNum" type="text" inputmode="numeric" maxlength="15" class="tph-del-input" placeholder="27123456">
                            </div>
                        </div>
                        <div class="tph-del-field">
                            <label class="tph-del-label" for="tph-tel-${esc(ctx)}">Teléfono <span class="tph-del-req">*</span></label>
                            <input id="tph-tel-${esc(ctx)}" data-ship="telefono" type="tel" maxlength="20" class="tph-del-input" placeholder="04141234567">
                        </div>
                        <div class="tph-del-field">
                            <label class="tph-del-label" for="tph-ag-${esc(ctx)}">Agencia <span class="tph-del-req">*</span></label>
                            <select id="tph-ag-${esc(ctx)}" data-ship="agencia" class="tph-del-select">${agOpts}</select>
                        </div>
                        <div class="tph-del-field">
                            <label class="tph-del-label" for="tph-est-${esc(ctx)}">Estado <span class="tph-del-req">*</span></label>
                            <select id="tph-est-${esc(ctx)}" data-ship="estado" class="tph-del-select">${statesOpts}</select>
                        </div>
                        <div class="tph-del-field full">
                            <label class="tph-del-label" for="tph-ciu-${esc(ctx)}">Ciudad o Municipio <span class="tph-del-req">*</span></label>
                            <input id="tph-ciu-${esc(ctx)}" data-ship="ciudad" type="text" maxlength="60" list="tph-cities-${esc(ctx)}" class="tph-del-input" placeholder="Selecciona estado y escribe o elige ciudad">
                            <datalist id="tph-cities-${esc(ctx)}"></datalist>
                        </div>
                        <div class="tph-del-field full">
                            <label class="tph-del-label" for="tph-ofi-${esc(ctx)}">Oficina o dirección de entrega <span class="tph-del-req">*</span></label>
                            <input id="tph-ofi-${esc(ctx)}" data-ship="oficina" type="text" maxlength="120" class="tph-del-input" placeholder="Ej: Oficina Paseo Las Mercedes / Av. Bolívar">
                        </div>
                        <div class="tph-del-field full">
                            <label class="tph-del-label" for="tph-mail-${esc(ctx)}">Correo electrónico (opcional)</label>
                            <input id="tph-mail-${esc(ctx)}" data-ship="correo" type="email" maxlength="90" class="tph-del-input" placeholder="Opcional (para notificaciones de agencia)">
                        </div>
                    </div>
                    <div class="tph-del-preview"></div>
                </div>

                <div class="tph-del-error-msg" hidden></div>
                <div class="tph-del-foot-bar">
                    <button type="button" class="tph-del-clear-btn">Solo retirar en tienda (sin entrega)</button>
                </div>
            </div>
        </div>`;

        const trigger = inst.containerEl.querySelector('.tph-del-trigger');
        trigger.addEventListener('click', () => {
            inst.isExpanded = !inst.isExpanded;
            updateTriggerSummary(inst);
            if (inst.isExpanded && inst.mode === 'delivery') {
                initMapIfNeeded(inst);
            }
        });

        inst.containerEl.querySelectorAll('.tph-del-tab').forEach((btn) => {
            btn.addEventListener('click', () => {
                setMode(inst, btn.getAttribute('data-mode'));
            });
        });

        const gpsBtn = inst.containerEl.querySelector('.tph-del-gps-btn');
        if (gpsBtn) gpsBtn.addEventListener('click', () => locateGPS(inst));

        const recenterBtn = inst.containerEl.querySelector('.tph-del-map-recenter');
        if (recenterBtn) recenterBtn.addEventListener('click', () => locateGPS(inst));

        const refInput = inst.containerEl.querySelector('.tph-del-ref-input');
        if (refInput) {
            refInput.value = inst.reference || '';
            refInput.addEventListener('input', () => {
                inst.reference = refInput.value;
                notifyChange(inst);
            });
        }

        const clearBtn = inst.containerEl.querySelector('.tph-del-clear-btn');
        if (clearBtn) clearBtn.addEventListener('click', () => clearSelection(inst));

        bindShippingInputs(inst);
        updateCityDatalist(inst);
        updateShippingPreview(inst);
        renderDeliveryStatus(inst);
        updateTriggerSummary(inst);
    }

    function getPublicState(inst) {
        return {
            context: inst.context,
            isExpanded: inst.isExpanded,
            mode: inst.mode,
            gpsLat: inst.gpsLat,
            gpsLng: inst.gpsLng,
            zone: inst.zone ? Object.assign({}, inst.zone) : null,
            outOfZone: inst.outOfZone,
            reference: inst.reference,
            shipping: normalizeShippingData(inst.shipping)
        };
    }

    const TPHDelivery = {
        mount(context, containerEl, options = {}) {
            if (!containerEl) return null;
            injectStyles();
            let inst = instances.get(context);
            if (!inst || inst.containerEl !== containerEl) {
                if (inst && inst.map) {
                    try { inst.map.remove(); } catch (e) {}
                }
                inst = createDefaultState(context);
                inst.containerEl = containerEl;
                inst.options = options || {};
                instances.set(context, inst);
                renderMarkup(inst);
            } else {
                inst.options = options || inst.options;
                updateTriggerSummary(inst);
            }
            return inst;
        },

        getState(context) {
            const inst = instances.get(context);
            return inst ? getPublicState(inst) : null;
        },

        getDeliveryFeeBs(context) {
            const inst = instances.get(context);
            if (!inst || inst.mode !== 'delivery' || !inst.zone) return 0;
            return Number(inst.zone.precio_bs || 0);
        },

        validate(context) {
            const inst = instances.get(context);
            if (!inst || !inst.mode) return { valid: true, error: '' };

            let error = '';
            if (inst.mode === 'delivery') {
                if (inst.gpsLat == null || inst.gpsLng == null) {
                    error = 'Presiona "Usar mi ubicación actual" o toca el mapa para fijar tu punto de delivery.';
                } else if (inst.outOfZone || !inst.zone) {
                    error = 'El punto marcado está fuera del área de delivery. Mueve el pin dentro de Caracas/Guarenas o selecciona Envío Nacional.';
                }
            } else if (inst.mode === 'shipping') {
                const s = normalizeShippingData(inst.shipping);
                const digitsDoc = String(inst.shipping.docNum || '').replace(/[^\d]/g, '');
                const digitsTel = s.telefono;
                if (!s.nombre || s.nombre.length < 3) {
                    error = 'Ingresa el nombre completo de quien recibe el envío.';
                } else if (digitsDoc.length < 6) {
                    error = 'Ingresa un número de Cédula o RIF válido (mínimo 6 dígitos).';
                } else if (digitsTel.length < 10) {
                    error = 'Ingresa un teléfono de contacto válido (ej: 04141234567).';
                } else if (!s.estado) {
                    error = 'Selecciona el Estado destino para el envío.';
                } else if (!s.ciudad || s.ciudad.length < 2) {
                    error = 'Indica la Ciudad o Municipio destino.';
                } else if (!s.oficinaClean || s.oficinaClean.length < 3) {
                    error = 'Indica la oficina de agencia o dirección de entrega.';
                }
            }

            inst.validationError = error;
            if (error) {
                inst.isExpanded = true;
                updateTriggerSummary(inst);
            }
            renderErrorBanner(inst);
            return { valid: !error, error };
        },

        formatWhatsAppAddon(context, productsTotalBs = 0) {
            const inst = instances.get(context);
            if (!inst || !inst.mode) return '';

            if (inst.mode === 'delivery' && inst.zone && inst.gpsLat != null) {
                const feeBs = Number(inst.zone.precio_bs || 0);
                const latStr = inst.gpsLat.toFixed(6);
                const lngStr = inst.gpsLng.toFixed(6);
                const mapsUrl = `https://www.google.com/maps?q=${latStr},${lngStr}`;
                const lines = [
                    `\n*Entrega por Delivery (${displayZoneName(inst.zone.nombre)}):* ${formatBs(feeBs)}`
                ];
                if (Number(productsTotalBs) > 0 && feeBs > 0) {
                    lines.push(`*Total estimado con Delivery:* ${formatBs(Number(productsTotalBs) + feeBs)}`);
                }
                lines.push(`Ubicación GPS: ${mapsUrl}`);
                const refClean = cleanSpaces(inst.reference);
                if (refClean) {
                    lines.push(`Referencia: ${refClean}`);
                }
                return lines.join('\n');
            }

            if (inst.mode === 'shipping') {
                const s = normalizeShippingData(inst.shipping);
                const lines = [
                    `\n*Datos de Envío Nacional (${s.agencia}):*`,
                    `Nombre: ${s.nombre}`,
                    `Cédula: ${s.cedula}`,
                    `Teléfono: ${s.telefono}`
                ];
                if (s.correo) {
                    lines.push(`Correo: ${s.correo}`);
                }
                lines.push(`Oficina donde recibe: ${s.oficinaCompleta}`);
                lines.push('Modalidad: Cobro en destino');
                return lines.join('\n');
            }

            return '';
        },

        reset(context) {
            const inst = instances.get(context);
            if (!inst) return;
            inst.mode = null;
            inst.isExpanded = false;
            inst.gpsLat = null;
            inst.gpsLng = null;
            inst.gpsAccuracy = null;
            inst.zone = null;
            inst.outOfZone = false;
            inst.gpsStatus = 'idle';
            inst.gpsError = '';
            inst.reference = '';
            inst.validationError = '';
            const refInput = inst.containerEl ? inst.containerEl.querySelector('.tph-del-ref-input') : null;
            if (refInput) refInput.value = '';
            renderDeliveryStatus(inst);
            renderErrorBanner(inst);
            updateTriggerSummary(inst);
        },

        // Utilidades expuestas para pruebas/integración
        _findMatchingZone: findMatchingZone,
        _normalizeShippingData: normalizeShippingData,
        _states: STATES_VE,
        _agencies: AGENCIES
    };

    global.TPHDelivery = TPHDelivery;
})(window);
