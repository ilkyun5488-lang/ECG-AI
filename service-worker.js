// 아주 단순한 캐시(오프라인에서 첫 화면 정도만 동작)
const CACHE_NAME = "ecg-learning-v27";
const ASSETS = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./manifest.json",
  "./assets/icon.svg",
  "./assets/ecg_nsr.svg",
  "./assets/ecg_af.svg",
  "./assets/ecg_sinus_tachy.svg",
  "./assets/ecg_sinus_brady.svg",
  "./assets/ecg_avblock_2nd.svg",
  "./assets/user/simus tachycardia.png",
  "./assets/user/atrial tachycardia.png",
  "./assets/user/atrial flutter.png",
  "./assets/user/AVRT.png",
  "./assets/user/AVNRT.png",
  "./assets/user/ventricular tachycardia.png",
  "./assets/user/Atrial fibrillation with LBBB.png",
  "./assets/user/Atrial fibrillation with WPW.png",
  "./assets/user/polymorphic ventricular tachycardia.png",
  "./assets/user/Torsades de Pointes.png",
  "./assets/user/ventricular fibrillation.png",
  "./assets/user/sinus bradycardia.png",
  "./assets/user/junctional escape rhythm.png",
  "./assets/user/1at degree AV block.png",
  "./assets/user/normal sinus rhythm.png",
  "./assets/user/RBBB.png",
  "./assets/user/LBBB.png",
  "./assets/user/WPW.png",
  "./assets/user/wandering atrial pacemaker.png",
  "./assets/user/sinus arrhythmia.png",
  "./assets/user/PAC.png",
  "./assets/user/tachy-brady syndrome.png",
  "./assets/user/PAC bigeminy.png",
  "./assets/user/non-conducted APC.png",
  "./assets/user/aberrant conduction.png",
  "./assets/user/2nd degree AV block Mobits Type 1.png",
  "./assets/user/2nd degree AV block Mobits Type 2.png",
  "./assets/user/High degree AV block.png",
  "./assets/user/sinus exit block.png",
  "./assets/user/sinus pause.png",
  "./assets/user/3rd degree AV Block.png",
  "./assets/user/ventricular escape rhythm.png",
  "./assets/user/VVI pacemaker.png",
  "./assets/user/DDD pacemaker.png",
  "./assets/user/failure to capture_ventricle.png",
  "./assets/user/failure to pace_atrial.png",
  "./assets/user/ST elevation MI.png",
  "./assets/user/long QT.png",
  "./assets/user/Brugada pattern.png",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k === CACHE_NAME ? null : caches.delete(k))))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});

