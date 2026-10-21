// Service Worker oficial de Todo Partes Horizonte
// Manejador de Notificaciones Push de Ofertas y Promociones

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { title: 'Todo Partes Horizonte', body: event.data.text() };
    }
  }

  const title = data.title || 'Todo Partes Horizonte';
  const options = {
    body: data.body || '¡Tenemos promociones especiales en repuestos para tu rústico!',
    icon: '/assets/apple-touch-icon.png',
    badge: '/assets/apple-touch-icon.png',
    vibrate: [200, 100, 200, 100, 200],
    data: {
      url: data.url || '/tarjeta.html'
    },
    actions: [
      { action: 'open', title: 'Ver Oferta' },
      { action: 'close', title: 'Cerrar' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'close') return;

  const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/tarjeta.html';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('tarjeta') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
