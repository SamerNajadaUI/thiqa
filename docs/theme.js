// المظهر: فاتح / غامق / حسب الجهاز.
// بيتحمّل بالـ<head> قبل ما تنرسم الصفحة عشان ما يصير وميض، وبيحط data-theme على <html>.
(() => {
  const KEY = "theme-pref";
  const root = document.documentElement;
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const read = () => { try { return localStorage.getItem(KEY) || "system"; } catch { return "system"; } };

  function apply() {
    const pref = read();
    const dark = pref === "dark" || (pref === "system" && mq.matches);
    root.dataset.theme = dark ? "dark" : "light";
    root.dataset.pref = pref;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? "#0E0F14" : "#F5F5F9";
    document.querySelectorAll("[data-theme-set]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.themeSet === pref)));
    document.querySelectorAll("[data-theme-cycle]").forEach((b) => { if (!window.themeToggle) return; b.innerHTML = iconFor(pref); b.setAttribute("aria-label", labelFor(pref)); b.title = labelFor(pref); });
  }

  const OPTIONS = [
    ["light", "فاتح", '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'],
    ["system", "حسب الجهاز", '<rect x="5" y="2.5" width="14" height="19" rx="3"/><path d="M10 18.5h4"/>'],
    ["dark", "غامق", '<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2z"/>'],
  ];
  // زر المظهر: ثلاث خيارات صغيرة جنب بعض
  window.themeSwitch = () => `<div class="theme-switch" role="group" aria-label="المظهر">${OPTIONS.map(([k, label, path]) =>
    `<button type="button" data-theme-set="${k}" aria-label="${label}" title="${label}" aria-pressed="${read() === k}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg></button>`).join("")}</div>`;

  // نسخة مصغّرة لشريط الألعاب: زر واحد بيلف بين الخيارات الثلاثة
  const iconFor = (k) => { const o = OPTIONS.find((x) => x[0] === k) || OPTIONS[1]; return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${o[2]}</svg>`; };
  const labelFor = (k) => "المظهر: " + (OPTIONS.find((x) => x[0] === k) || OPTIONS[1])[1];
  window.themeToggle = () => `<button type="button" class="theme-toggle" data-theme-cycle aria-label="${labelFor(read())}" title="${labelFor(read())}">${iconFor(read())}</button>`;

  // رسالة صغيرة تحت بتوضّح شو صار
  let toastTimer = null;
  function toast(text) {
    let t = document.getElementById("ui-toast");
    if (!t) { t = document.createElement("div"); t.id = "ui-toast"; t.className = "ui-toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = text; t.classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("on"), 1400);
  }
  window.uiToast = toast;
  const save = (k) => { try { localStorage.setItem(KEY, k); } catch {} apply(); };
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-theme-set]");
    if (b) return save(b.dataset.themeSet);
    const c = e.target.closest("[data-theme-cycle]");
    if (c) { const order = ["system", "light", "dark"]; const next = order[(order.indexOf(read()) + 1) % 3]; save(next); toast(labelFor(next)); }
  });
  mq.addEventListener ? mq.addEventListener("change", apply) : mq.addListener(apply);
  window.addEventListener("storage", (e) => { if (e.key === KEY) apply(); });
  document.addEventListener("DOMContentLoaded", apply);
  apply();
})();
