// قائمة الألعاب: مكان واحد لكل الألعاب، بتستعملها الرئيسية وصفحة الألعاب.
const GAME_ICON = {
  points: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M17.5 14v7M14 17.5h7"/>',
  mafia: '<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2z"/><path d="M16 3.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" fill="currentColor"/>',
  who: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/><path d="M18 3.5c1.2.4 2 1.4 2 2.6 0 1.8-2 2-2 3.4M18 12h.01"/>',
  numbers: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/>',
  career: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
  qisma: '<path d="M6 3l12 18M18 3L6 21"/><circle cx="6" cy="18" r="2.6"/><circle cx="18" cy="18" r="2.6"/>',
  barra: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c.8-3.5 3.2-5.5 6-5.5s5.2 2 6 5.5M15 14.6c2.6-.4 5 1.3 6 5.4"/>',
};
const GAMES = [
  { id: "points", href: "points.html", name: "جمع نقاط", desc: "75 قسم بصور وأصوات وفيديو، وكروت سرقة", tags: ["👥 2–5 فرق", "🌐 أونلاين"], flag: "🔥 الأقوى" },
  { id: "qisma", href: "qisma.html", name: "قسمة ونصيب", desc: "إنت بتقسم وهم بيختاروا... بس إنت الوحيد اللي شايف الورق!", tags: ["👥 1–5", "🤖 ضد الكمبيوتر"], flag: "✨ جديد" },
  { id: "mafia", href: "mafia.html", name: "مافيا", desc: "مين المافيا بيناتنا؟ ليل ونهار وتصويت", tags: ["👥 4–16", "🌐 أونلاين"] },
  { id: "who", href: "#who", name: "احزر اللاعب", desc: "صاحبك بيسأل آه أو لا لحد ما يعرف اللاعب", tags: ["👥 2–5", "📱 تلفون واحد"] },
  { id: "numbers", href: "numbers.html", name: "الرقم الأقرب", desc: "مين أقرب للرقم الصح؟ آلاف الأسئلة", tags: ["👥 2+", "🌐 أونلاين"] },
  { id: "career", href: "career.html", name: "مسيرة لاعب", desc: "شعارات أنديته بتطلع وحدة وحدة، مين بيعرفه أول؟", tags: ["👥 2", "🌐 أونلاين"] },
  { id: "barra", href: "barra.html", name: "برا السالفة", desc: "كلمة الكل بيعرفها... إلا واحد!", tags: ["👥 3–20", "📱 تلفون واحد"] },
];

// base: المسار لمجلد الألعاب ("games/" من الرئيسية، "" من صفحة الألعاب)
function gamesGrid(base = "") {
  return `<div class="games-grid">${GAMES.map((g) => `<a class="gcard g-${g.id}" href="${base}${g.href}" data-game="${g.id}">
    <span class="art">${g.flag ? `<span class="flag">${g.flag}</span>` : ""}<span class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${GAME_ICON[g.id]}</svg></span></span>
    <span class="body"><b>${g.name}</b><small>${g.desc}</small><span class="tags">${g.tags.map((t) => `<span>${t}</span>`).join("")}</span></span>
  </a>`).join("")}</div>`;
}
