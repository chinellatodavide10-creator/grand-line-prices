// Tiene in memoria la "scocca" dell'app per aprirla anche senza rete. Prima prova sempre la rete, cosi gli aggiornamenti arrivano subito.
const C="glp-shell-v1",OK=/(\/|index\.html|manifest\.webmanifest|icon[^/]*\.png)$/;
self.addEventListener("install",e=>self.skipWaiting());
self.addEventListener("activate",e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(k!==C)await caches.delete(k);await self.clients.claim()})()));
self.addEventListener("fetch",e=>{const r=e.request,u=new URL(r.url);if(r.method!=="GET"||u.origin!==location.origin||!(r.mode==="navigate"||OK.test(u.pathname)))return;e.respondWith((async()=>{try{const n=await fetch(r);if(n&&n.ok){const c=await caches.open(C);c.put(r,n.clone())}return n}catch(x){const m=await caches.match(r)||await caches.match("index.html")||await caches.match("./");if(m)return m;throw x}})())});
