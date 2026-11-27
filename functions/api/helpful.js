// "도움이 됐어요" 실제 카운트. KV 바인딩 HELPFUL 이 없으면 숫자 없이 동작.
const ok = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const valid = (id) => typeof id === "string" && /^[A-Za-z0-9_-]{4,40}$/.test(id);

export async function onRequestGet({ request, env }) {
  const id = new URL(request.url).searchParams.get("id");
  if (!valid(id)) return ok({ error: "bad id" }, 400);
  if (!env.HELPFUL) return ok({ n: null });
  return ok({ n: parseInt((await env.HELPFUL.get("c:" + id)) || "0", 10) });
}

export async function onRequestPost({ request, env }) {
  let id;
  try { id = (await request.json()).id; } catch { return ok({ error: "bad body" }, 400); }
  if (!valid(id)) return ok({ error: "bad id" }, 400);
  if (!env.HELPFUL) return ok({ n: null });
  const ip = request.headers.get("cf-connecting-ip") || "x";
  const once = "v:" + id + ":" + ip;               // 같은 사람(IP) 하루 1번만
  let n = parseInt((await env.HELPFUL.get("c:" + id)) || "0", 10);
  if (!(await env.HELPFUL.get(once))) {
    n += 1;
    await env.HELPFUL.put("c:" + id, String(n));
    await env.HELPFUL.put(once, "1", { expirationTtl: 86400 });
  }
  return ok({ n });
}
