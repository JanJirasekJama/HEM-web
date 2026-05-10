const CACHE_NAME = 'hem-shell-v2'
const OFFLINE_URL = '/offline.html'
const ASSETS = ['/', OFFLINE_URL, '/manifest.webmanifest', '/pwa-icon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET' || !request.url.startsWith('http')) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request))
    return
  }

  if (new URL(request.url).origin !== self.location.origin) return

  event.respondWith(cacheFirstStaticAsset(request))
})

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request)
    return response
  } catch {
    return (await caches.match(OFFLINE_URL)) || Response.error()
  }
}

async function cacheFirstStaticAsset(request) {
  const cached = await caches.match(request)
  if (cached) return cached

  const response = await fetch(request)
  if (response.ok && response.type === 'basic') {
    const cache = await caches.open(CACHE_NAME)
    cache.put(request, response.clone())
  }

  return response
}
