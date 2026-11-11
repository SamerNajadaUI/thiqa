// عناصر واجهة مشتركة: شريط التبويب السفلي، رأس الصفحة، وبيانات اللاعب.
(function () {
  const ROOT = new URL("../", document.currentScript.src).href;
  const I = (p) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
  const TABS = [
    ["home", "home.html", "الرئيسية", '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>'],
    ["games", "games/", "الألعاب", '<rect x="3" y="8" width="18" height="11" rx="5"/><path d="M8 11.5v4M6 13.5h4M16 12.5h.01M18 14.5h.01"/>'],
    ["rewards", "rewards.html", "المكافآت", '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3M12 14v4M8 20h8"/>'],
    ["settings", "settings.html", "الإعدادات", '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'],
  ];
  const AppUI = {
    ROOT,
    tabs(active) {
      document.querySelectorAll(".apptabs").forEach((n) => n.remove());
      const nav = document.createElement("nav");
      nav.className = "apptabs"; nav.setAttribute("aria-label", "التنقل");
      nav.innerHTML = TABS.map(([id, href, label, ic]) => `<a href="${ROOT}${href}" ${id === active ? 'aria-current="page"' : ""}>${I(ic)}<span>${label}</span></a>`).join("");
      document.body.appendChild(nav);
      return nav;
    },
    initial(name) { return (String(name || "؟").trim()[0] || "؟"); },
    esc: (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
    // وين نرجّع اللاعب بعد الدخول: بس مسارات من نفس الموقع
    safeNext(raw) { try { const u = new URL(raw, location.origin); return u.origin === location.origin && u.pathname.startsWith(new URL(ROOT).pathname) ? u.pathname + u.search + u.hash : ROOT + "home.html"; } catch { return ROOT + "home.html"; } },
    planBadge(plan) { const p = Rewards.PLANS[plan] || Rewards.PLANS.free; return `<span class="badge${Rewards.isPlus(plan) ? " plus" : ""}">${p.name}</span>`; },
    sheet(html) {
      const back = document.createElement("div"); back.className = "sheet-back";
      back.innerHTML = `<div class="sheet" role="dialog" aria-modal="true"><span class="grip"></span>${html}</div>`;
      back.addEventListener("click", (e) => { if (e.target === back) back.remove(); });
      document.body.appendChild(back); return back;
    },
  };
  window.AppUI = AppUI;
})();
