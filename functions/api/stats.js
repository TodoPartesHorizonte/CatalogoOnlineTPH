/**
 * Cloudflare Pages Function: GET /api/stats
 * Devuelve el historial analítico almacenado en Cloudflare KV (hora Caracas UTC-4)
 */

export function getCaracasDateString(now = new Date()) {
    const caracasMs = now.getTime() - (4 * 60 * 60 * 1000);
    return new Date(caracasMs).toISOString().split("T")[0];
}

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
        const url = new URL(request.url);
        const rawDays = parseInt(url.searchParams.get("days") || "90", 10);
        const daysLimit = Number.isFinite(rawDays) ? Math.max(1, Math.min(365, rawDays)) : 90;

        const keyNames = [];
        let cursor = undefined;
        for (let page = 0; page < 20; page++) {
            const listResult = await env.STATS_KV.list({ prefix: "stats_daily:", cursor });
            for (const key of (listResult.keys || [])) {
                if (key && key.name && key.name.startsWith("stats_daily:")) {
                    keyNames.push(key.name);
                }
            }
            if (listResult.list_complete || !listResult.cursor) {
                break;
            }
            cursor = listResult.cursor;
        }

        const uniqueSortedKeys = Array.from(new Set(keyNames)).sort((a, b) => b.localeCompare(a));
        const targetKeys = uniqueSortedKeys.slice(0, daysLimit);
        const values = await Promise.all(targetKeys.map(k => env.STATS_KV.get(k)));

        const daily_history = [];
        for (let i = 0; i < targetKeys.length; i++) {
            if (values[i]) {
                try {
                    daily_history.push({
                        date: targetKeys[i].replace("stats_daily:", ""),
                        data: JSON.parse(values[i])
                    });
                } catch (e) {
                    // Ignorar registros corruptos
                }
            }
        }

        return new Response(JSON.stringify({
            ok: true,
            today_caracas: getCaracasDateString(new Date()),
            total_days_available: uniqueSortedKeys.length,
            total_days_tracked: daily_history.length,
            latest_date: uniqueSortedKeys.length > 0 ? uniqueSortedKeys[0].replace("stats_daily:", "") : null,
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
