/**
 * Cloudflare Pages Function: POST /api/track-event
 * Recopila eventos de interacción del catálogo online de repuestos
 */

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
            body = JSON.parse(rawText);
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

        const today = new Date().toISOString().split("T")[0];
        const dailyKey = `stats_daily:${today}`;

        let statsDaily = {
            page_views: 0,
            whatsapp_clicks_total: 0,
            searches_count: 0,
            pages: {},
            products: {},
            searches: {},
            vehicle_filters: {}
        };

        const rawDaily = await env.STATS_KV.get(dailyKey);
        if (rawDaily) {
            try {
                const parsed = JSON.parse(rawDaily);
                statsDaily.page_views = parsed.page_views || 0;
                statsDaily.whatsapp_clicks_total = parsed.whatsapp_clicks_total || 0;
                statsDaily.searches_count = parsed.searches_count || 0;
                statsDaily.pages = parsed.pages || {};
                statsDaily.products = parsed.products || {};
                statsDaily.searches = parsed.searches || {};
                statsDaily.vehicle_filters = parsed.vehicle_filters || {};
            } catch (e) {
                // Si falla el parseo, conservamos el objeto inicial
            }
        }

        switch (eventType) {
            case "page_view": {
                statsDaily.page_views += 1;
                const pagePath = String(data.path || "/").trim() || "/";
                if (!statsDaily.pages) statsDaily.pages = {};
                statsDaily.pages[pagePath] = (statsDaily.pages[pagePath] || 0) + 1;
                break;
            }

            case "product_view": {
                const pId = String(data.product_id || "").trim();
                if (pId) {
                    if (!statsDaily.products[pId]) {
                        statsDaily.products[pId] = {
                            name: data.product_name || "Repuesto",
                            model: data.product_model || "",
                            photo: data.product_photo || "",
                            views: 0,
                            whatsapp_clicks: 0
                        };
                    } else {
                        if (data.product_name) statsDaily.products[pId].name = data.product_name;
                        if (data.product_model) statsDaily.products[pId].model = data.product_model;
                        if (data.product_photo) statsDaily.products[pId].photo = data.product_photo;
                    }
                    statsDaily.products[pId].views += 1;
                }
                break;
            }

            case "whatsapp_click": {
                statsDaily.whatsapp_clicks_total += 1;
                const pId = String(data.product_id || "").trim();
                if (pId) {
                    if (!statsDaily.products[pId]) {
                        statsDaily.products[pId] = {
                            name: data.product_name || "Repuesto",
                            model: data.product_model || "",
                            photo: data.product_photo || "",
                            views: 0,
                            whatsapp_clicks: 0
                        };
                    } else {
                        if (data.product_name) statsDaily.products[pId].name = data.product_name;
                        if (data.product_model) statsDaily.products[pId].model = data.product_model;
                        if (data.product_photo) statsDaily.products[pId].photo = data.product_photo;
                    }
                    statsDaily.products[pId].whatsapp_clicks += 1;
                }
                break;
            }

            case "search": {
                const query = String(data.query || "").trim().toLowerCase().slice(0, 80);
                if (query.length >= 2) {
                    statsDaily.searches_count += 1;
                    statsDaily.searches[query] = (statsDaily.searches[query] || 0) + 1;
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
