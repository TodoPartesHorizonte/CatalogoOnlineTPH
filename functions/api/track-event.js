/**
 * Cloudflare Pages Function: POST /api/track-event
 * Recopila eventos de interacción del catálogo online de repuestos
 */

const ALLOWED_SECONDARY_ACTIONS = new Set([
    "share",
    "oem_copy",
    "instagram",
    "facebook",
    "maps",
    "reviews",
    "phone_call",
    "save_contact",
    "push_subscribe"
]);

export function getCaracasDateString(now = new Date()) {
    const caracasMs = now.getTime() - (4 * 60 * 60 * 1000);
    return new Date(caracasMs).toISOString().split("T")[0];
}

function upsertProductEntry(productsMap, item) {
    const pId = String((item && item.product_id) || "").trim();
    if (!pId) return null;

    if (!productsMap[pId]) {
        productsMap[pId] = {
            name: (item && item.product_name) || "Repuesto",
            model: (item && item.product_model) || "",
            photo: (item && item.product_photo) || "",
            views: 0,
            cart_adds: 0,
            whatsapp_clicks: 0
        };
    } else {
        if (item.product_name) productsMap[pId].name = item.product_name;
        if (item.product_model) productsMap[pId].model = item.product_model;
        if (item.product_photo) productsMap[pId].photo = item.product_photo;
        if (typeof productsMap[pId].cart_adds !== "number") productsMap[pId].cart_adds = 0;
    }
    return productsMap[pId];
}

export async function onRequestPost(context) {
    const { request, env } = context;

    if (!env.STATS_KV) {
        return new Response(JSON.stringify({ ok: false, error: "STATS_KV not configured" }), {
            status: 503,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        });
    }

    try {
        let body = {};
        const rawText = await request.text();
        try {
            body = rawText ? JSON.parse(rawText) : {};
        } catch (e) {
            body = {};
        }
        const eventType = body.event;
        const data = body.data || {};

        if (!eventType) {
            return new Response(JSON.stringify({ ok: false, error: "Missing event type" }), {
                status: 400,
                headers: {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            });
        }

        const today = getCaracasDateString(new Date());
        const dailyKey = `stats_daily:${today}`;

        let statsDaily = {
            page_views: 0,
            whatsapp_clicks_total: 0,
            add_to_cart_total: 0,
            searches_count: 0,
            pages: {},
            products: {},
            searches: {},
            zero_result_searches: {},
            vehicle_filters: {},
            cta_sources: {},
            secondary_actions: {}
        };

        const rawDaily = await env.STATS_KV.get(dailyKey);
        if (rawDaily) {
            try {
                const parsed = JSON.parse(rawDaily);
                statsDaily.page_views = parsed.page_views || 0;
                statsDaily.whatsapp_clicks_total = parsed.whatsapp_clicks_total || 0;
                statsDaily.add_to_cart_total = parsed.add_to_cart_total || 0;
                statsDaily.searches_count = parsed.searches_count || 0;
                statsDaily.pages = parsed.pages || {};
                statsDaily.products = parsed.products || {};
                statsDaily.searches = parsed.searches || {};
                statsDaily.zero_result_searches = parsed.zero_result_searches || {};
                statsDaily.vehicle_filters = parsed.vehicle_filters || {};
                statsDaily.cta_sources = parsed.cta_sources || {};
                statsDaily.secondary_actions = parsed.secondary_actions || {};
            } catch (e) {
                // Si falla el parseo, conservamos el objeto inicial
            }
        }

        switch (eventType) {
            case "page_view": {
                statsDaily.page_views += 1;
                const pagePath = String(data.path || "/").trim() || "/";
                statsDaily.pages[pagePath] = (statsDaily.pages[pagePath] || 0) + 1;
                break;
            }

            case "product_view": {
                const entry = upsertProductEntry(statsDaily.products, data);
                if (entry) {
                    entry.views += 1;
                }
                break;
            }

            case "add_to_cart": {
                statsDaily.add_to_cart_total += 1;
                const entry = upsertProductEntry(statsDaily.products, data);
                if (entry) {
                    entry.cart_adds = (entry.cart_adds || 0) + 1;
                }
                break;
            }

            case "whatsapp_click": {
                statsDaily.whatsapp_clicks_total += 1;
                const source = String(data.source || data.origen || "directo").trim().toLowerCase().slice(0, 40) || "directo";
                statsDaily.cta_sources[source] = (statsDaily.cta_sources[source] || 0) + 1;

                if (Array.isArray(data.items) && data.items.length > 0) {
                    const seenIds = new Set();
                    for (const item of data.items) {
                        const pId = String((item && item.product_id) || "").trim();
                        if (!pId || seenIds.has(pId)) continue;
                        seenIds.add(pId);
                        const entry = upsertProductEntry(statsDaily.products, item);
                        if (entry) {
                            entry.whatsapp_clicks += 1;
                        }
                    }
                } else {
                    const entry = upsertProductEntry(statsDaily.products, data);
                    if (entry) {
                        entry.whatsapp_clicks += 1;
                    }
                }
                break;
            }

            case "search": {
                const query = String(data.query || "").trim().toLowerCase().slice(0, 80);
                if (query.length >= 2) {
                    statsDaily.searches_count += 1;
                    statsDaily.searches[query] = (statsDaily.searches[query] || 0) + 1;
                    if (data.results_count === 0) {
                        statsDaily.zero_result_searches[query] = (statsDaily.zero_result_searches[query] || 0) + 1;
                    }
                }
                break;
            }

            case "filter_vehicle": {
                const slug = String(data.model_slug || "").trim().toLowerCase().slice(0, 80);
                if (slug) {
                    statsDaily.vehicle_filters[slug] = (statsDaily.vehicle_filters[slug] || 0) + 1;
                }
                break;
            }

            case "secondary_action": {
                const action = String(data.action || "").trim().toLowerCase().slice(0, 30);
                if (action && ALLOWED_SECONDARY_ACTIONS.has(action)) {
                    statsDaily.secondary_actions[action] = (statsDaily.secondary_actions[action] || 0) + 1;
                }
                break;
            }
        }

        // Guardar estadísticas diarias con TTL de 90 días (7,776,000 segundos)
        await env.STATS_KV.put(dailyKey, JSON.stringify(statsDaily), { expirationTtl: 7776000 });

        return new Response(JSON.stringify({ ok: true }), {
            status: 200,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        });
    } catch (err) {
        return new Response(JSON.stringify({ ok: false, error: err.message || "Server error" }), {
            status: 500,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        });
    }
}

export async function onRequestOptions() {
    return new Response(null, {
        status: 204,
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    });
}
