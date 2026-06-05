/* ─────────────────────────────────────────────────────
   헬씨루틴 서비스 워커 — 복약 알림 스케줄링
───────────────────────────────────────────────────── */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

/* 메인 스레드에서 알림 요청을 받아 처리 */
self.addEventListener("message", (event) => {
  if (event.data?.type === "SHOW_NOTIFICATION") {
    const { title, body, tag } = event.data;
    self.registration.showNotification(title, {
      body,
      tag,
      icon: "/chat-button.png",
      badge: "/chat-button.png",
      requireInteraction: false,
    });
  }
});

/* Push 이벤트 (서버 푸시 연동 시 사용) */
self.addEventListener("push", (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title ?? "헬씨루틴", {
      body: data.body ?? "",
      icon: "/chat-button.png",
    })
  );
});

/* 알림 클릭 시 앱 포커스 */
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      if (clients.length > 0) return clients[0].focus();
      return self.clients.openWindow("/");
    })
  );
});
