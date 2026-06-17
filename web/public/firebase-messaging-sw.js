importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyAmuXetNP0tC-kPAcJYMav5QgqPeK-co_c",
  authDomain: "carelog-1161d.firebaseapp.com",
  projectId: "carelog-1161d",
  storageBucket: "carelog-1161d.firebasestorage.app",
  messagingSenderId: "359232054030",
  appId: "1:359232054030:web:3617963a3f44263f4f2d5f",
});

const messaging = firebase.messaging();

/* 백그라운드 수신 푸시 처리 */
messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification ?? {};
  self.registration.showNotification(title ?? "헬씨루틴", {
    body: body ?? "",
    icon: "/chat-button.png",
    badge: "/chat-button.png",
  });
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      if (clients.length > 0) return clients[0].focus();
      return self.clients.openWindow("/");
    })
  );
});
