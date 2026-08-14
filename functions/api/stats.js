/**
 * Cloudflare Pages Function: GET /api/stats
 * Devuelve el historial analítico de los últimos 90 días almacenado en Cloudflare KV
 */

export async function onRequestGet(context) {
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

    const authHeader = request.headers.get("Authorization") || "";
    const token = authHeader.replace("Bearer ", "").trim();
    const expectedToken = env.STATS_AUTH_TOKEN || "";

    // Si hay un token configurado en Cloudflare, validar autorización
    if (expectedToken && token !== expectedToken) {
        return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), {
            status: 401,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        });
    }

    try {
        const now = new Date();
        const daily_history = [];
        const promises = [];
        const dates = [];

        // Consultar los últimos 90 días en paralelo
        for (let i = 89; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            const dateStr = d.toISOString().split("T")[0];
            dates.push(dateStr);
            promises.push(env.STATS_KV.get(`stats_daily:${dateStr}`));
        }

        const results = await Promise.all(promises);
        for (let i = 0; i < dates.length; i++) {
            if (results[i]) {
                try {
                    daily_history.push({
                        date: dates[i],
                        data: JSON.parse(results[i])
                    });
                } catch (e) {
                    // Ignorar registros corruptos
                }
            }
        }

        return new Response(JSON.stringify({
            ok: true,
            total_days_tracked: daily_history.length,
            daily_history
        }), {
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
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    });
}
