/**
 * Cloudflare Pages Function: /api/marketing-subscribe
 * Gestiona el registro y consulta de suscripciones Web Push para la Tarjeta Digital de Todo Partes Horizonte.
 */

function generateId(endpoint) {
  let hash = 0;
  for (let i = 0; i < endpoint.length; i++) {
    hash = ((hash << 5) - hash) + endpoint.charCodeAt(i);
    hash |= 0;
  }
  return 'sub_' + Math.abs(hash).toString(36) + '_' + endpoint.slice(-16).replace(/[^a-zA-Z0-9]/g, '');
}

export async function onRequestPost(context) {
  const { request, env } = context;

  if (!env.STATS_KV) {
    return new Response(JSON.stringify({ success: false, error: "STATS_KV no está configurado en Cloudflare Pages" }), {
      status: 503,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }

  try {
    let body = {};
    try {
      body = await request.json();
    } catch (e) {
      body = {};
    }

    const sub = body.subscription || body;
    if (!sub || !sub.endpoint || !sub.keys || !sub.keys.p256dh || !sub.keys.auth) {
      return new Response(JSON.stringify({ success: false, error: "Datos de suscripción push incompletos." }), {
        status: 400,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*"
        }
      });
    }

    const subId = generateId(sub.endpoint);
    const ip = request.headers.get("cf-connecting-ip") || request.headers.get("x-forwarded-for") || "";
    const userAgent = request.headers.get("user-agent") || "";

    const subscriberRecord = {
      id: subId,
      endpoint: sub.endpoint,
      keys: {
        p256dh: sub.keys.p256dh,
        auth: sub.keys.auth
      },
      ip: ip,
      user_agent: userAgent.slice(0, 250),
      created_at: new Date().toISOString(),
      activo: 1
    };

    // Leer el registro global de suscriptores
    let registry = {};
    try {
      const raw = await env.STATS_KV.get("push_sub_registry");
      if (raw) {
        registry = JSON.parse(raw);
      }
    } catch (e) {
      registry = {};
    }

    // Guardar o actualizar suscriptor
    registry[subId] = subscriberRecord;

    // Guardar en Cloudflare KV
    await env.STATS_KV.put("push_sub_registry", JSON.stringify(registry));

    return new Response(JSON.stringify({
      success: true,
      message: "¡Suscripción guardada exitosamente!",
      id: subId
    }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ success: false, error: err.message || "Error en el servidor" }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }
}

export async function onRequestGet(context) {
  const { env } = context;

  if (!env.STATS_KV) {
    return new Response(JSON.stringify({ success: false, error: "STATS_KV no está configurado en Cloudflare Pages" }), {
      status: 503,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }

  try {
    const raw = await env.STATS_KV.get("push_sub_registry");
    const registry = raw ? JSON.parse(raw) : {};
    const subscribers = Object.values(registry);

    return new Response(JSON.stringify({
      success: true,
      total: subscribers.length,
      subscribers: subscribers
    }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ success: false, error: err.message }), {
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
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
  });
}
