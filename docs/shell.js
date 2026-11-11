// قائمة الألعاب: مكان واحد لكل الألعاب، بتستعملها الرئيسية وصفحة الألعاب.
const GAME_ICON = {
  points: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M17.5 14v7M14 17.5h7"/>',
  mafia: '<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2z"/><path d="M16 3.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" fill="currentColor"/>',
  who: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/><path d="M18 3.5c1.2.4 2 1.4 2 2.6 0 1.8-2 2-2 3.4M18 12h.01"/>',
  numbers: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/>',
  career: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
  qisma: '<path d="M6 3l12 18M18 3L6 21"/><circle cx="6" cy="18" r="2.6"/><circle cx="18" cy="18" r="2.6"/>',
  tamaa: '<circle cx="11" cy="14" r="6.5"/><path d="M15.5 9.5l2-2M18 5l1-1M19.5 7.5H21M16.5 4.5V3"/>',
  speed: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  catch: '<path d="M4 9h16l-2 11H6z"/><path d="M8 9l4-5 4 5"/>',
  anagram: '<path d="M4 18l4-12 4 12M5.5 14h5"/><path d="M15 7h6M15 12h6M15 17h6"/>',
  simon: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
  kworld: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
  karab: '<path d="M15 4a8 8 0 1 0 5 13A7 7 0 0 1 15 4z"/><path d="M17 8l.7 1.6 1.8.2-1.3 1.2.4 1.8-1.6-.9-1.6.9.4-1.8L14.5 9.8l1.8-.2z"/>',
  kucl: '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4M12 14v4M8 20h8"/>',
  kepl: '<path d="M4 18l2-9 4 4 2-7 2 7 4-4 2 9z"/><path d="M4 21h16"/>',
  kguess: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/><path d="M18 3.5c1.2.4 2 1.4 2 2.6 0 1.8-2 2-2 3.4"/>',
  kemoji: '<circle cx="12" cy="12" r="9"/><path d="M8 14c1 1.6 2.4 2.4 4 2.4s3-.8 4-2.4M9 9.5h.01M15 9.5h.01"/>',
  kkits: '<path d="M8 3l-5 3 2 5 2-1v11h10V10l2 1 2-5-5-3c-.5 1.5-2 2.5-4 2.5S8.5 4.5 8 3z"/>',
  khair: '<path d="M5 13c0-5 3-9 7-9s7 4 7 9"/><path d="M5 13c2-2 4-5 5-8M19 13c-2-2-4-4-6-8M8 13c2-1 4-3 5-6"/><path d="M6 15c1 3 3.2 5 6 5s5-2 6-5"/>',
  duel: '<circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M2 20c.6-3.4 2.8-5 6-5M22 20c-.6-3.4-2.8-5-6-5M9 20c.5-2.6 1.6-4 3-4s2.5 1.4 3 4"/>',
  ball: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5l3.2 2.3-1.2 3.7h-4l-1.2-3.7z"/><path d="M12 3v4.5M20.5 9.3l-5.3.5M17.5 19.5l-3.5-6M6.5 19.5l3.5-6M3.5 9.3l5.3.5"/>',
  hotcold: '<path d="M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0z"/><path d="M12 9v6"/>',
  dots: '<path d="M4 4h16v16H4z"/><path d="M4 12h16M12 4v16"/>',
  connect: '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="8" cy="12" r="2"/><circle cx="16" cy="12" r="2"/>',
  auction: '<path d="M14 4l6 6-3 3-6-6z"/><path d="M9 9l-6 6 4 4 6-6"/><path d="M3 21h9"/>',
  pictionary: '<path d="M16 3l5 5L9 20H4v-5z"/><path d="M13 6l5 5"/>',
  wheel: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6L5.6 18.4"/>',
  sahra: '<path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z"/><path d="M5 19h14"/>',
  hasm: '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3M12 14v4M8 20h8"/>',
  barra: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c.8-3.5 3.2-5.5 6-5.5s5.2 2 6 5.5M15 14.6c2.6-.4 5 1.3 6 5.4"/>',
};
// الأقسام: كل لعبة إلها قسم، والصفحة الرئيسية بتعرضهم كل قسم لحاله
const SECTIONS = [
  { id: "top", name: "الأشهر" },
  { id: "kora", name: "كرة قدم" },
  { id: "fast", name: "سرعة وأكشن" },
  { id: "think", name: "ذاكرة وتفكير" },
  { id: "strat", name: "استراتيجية وحظ" },
  { id: "group", name: "جماعية" },
];
const NEW = "🆕 جديدة";
const GAMES = [
  { id: "hasm", href: "hasm.html", sec: "top", name: "ليلة الحسم", desc: "كل واحد رئيس نادي: مزاد نجوم، ألغاز، وحرب أعصاب بالملعب", tags: ["👥 1–6", "🌐 غرفة أو 🤖"], flag: "🏆 الأقوى" },
  { id: "sahra", href: "sahra.html", sec: "top", name: "ملك السهرة", desc: "10 مراحل: ركلات ترجيح، كذب، تمثيل، قنبلة... وسهرة كروية", tags: ["👥 3–8", "🌐 غرفة أو تلفون"], flag: "👑 ملك السهرات" },
  { id: "points", href: "points.html", sec: "top", name: "جمع نقاط", desc: "110 قسم بصور وأصوات وفيديو، وكروت سرقة", tags: ["👥 2–5 فرق", "🌐 أونلاين"], flag: "الأشهر" },
  { id: "tamaa", href: "tamaa.html", sec: "top", name: "لا تطمع", desc: "اكشف مربعات واجمع ذهب، ووقّف قبل القنبلة 💣", tags: ["👥 1–6", "🤖 ضد الكمبيوتر"], flag: "✨ جديد" },
  { id: "mafia", href: "mafia.html", sec: "top", name: "مافيا", desc: "مين المافيا بيناتنا؟ ليل ونهار وتصويت", tags: ["👥 4–16", "🌐 أونلاين"] },
  { id: "who", href: "#who", sec: "top", name: "احزر اللاعب", desc: "صاحبك بيسأل آه أو لا لحد ما يعرف اللاعب", tags: ["👥 2–5", "📱 تلفون واحد"] },
  { id: "kworld", href: "kworld.html", sec: "kora", name: "كرة عالمية", desc: "كأس العالم، الدوريات الكبيرة، الملاعب، المدربين والشعارات", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "karab", href: "karab.html", sec: "kora", name: "كرة عربية", desc: "النشامى، الدوري السعودي، نجوم العرب ومعلقينهم", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "kucl", href: "kucl.html", sec: "kora", name: "دوري الأبطال", desc: "نهائيات، هدافين، ريمونتادات، وموسم 26/27", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "kepl", href: "kepl.html", sec: "kora", name: "الدوري الإنجليزي", desc: "أبطال البريميرليغ وهدافينه وملاعبه", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "kguess", href: "kguess.html", sec: "kora", name: "خمّن اللاعب", desc: "تلميحات بتطلع وحدة وحدة، اعرفه بأقل عدد", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "kemoji", href: "kemoji.html", sec: "kora", name: "خمّن بالإيموجي", desc: "إيموجي بيوصف لاعب أو نادي أو بطولة", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "kkits", href: "kkits.html", sec: "kora", name: "أطقم الأندية", desc: "طقم مرسوم بدون شعار، من ألوانه اعرف النادي", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "khair", href: "khair.html", sec: "kora", name: "تسريحة لاعب", desc: "بتشوف بس شعره، اعرف مين هو", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "duel", href: "duel.html", sec: "kora", name: "تحدي اللاعبين", desc: "فريق بيخبّي لاعب والثاني بيسأل آه أو لا، 60 ثانية لكل سؤال", tags: ["👥 فريقين", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "ball", href: "ball.html", sec: "kora", name: "أين الكرة", desc: "التمريرة طارت والكرة اختفت، اتبع الخط وحدد مكانها", tags: ["👥 1–10", "🌐 غرفة أو تلفون"], flag: NEW },
  { id: "numbers", href: "numbers.html", sec: "top", name: "الرقم الأقرب", desc: "مين أقرب للرقم الصح؟ آلاف الأسئلة", tags: ["👥 2+", "🌐 أونلاين"] },
  { id: "career", href: "career.html", sec: "top", name: "مسيرة لاعب", desc: "شعارات أنديته بتطلع وحدة وحدة، مين بيعرفه أول؟", tags: ["👥 2", "🌐 أونلاين"] },
  { id: "qisma", href: "qisma.html", sec: "top", name: "قسمة ونصيب", desc: "إنت بتقسم وهم بيختاروا... بس إنت شايف الورق", tags: ["👥 1–5", "🤖 ضد الكمبيوتر"] },
  { id: "barra", href: "barra.html", sec: "top", name: "برا السالفة", desc: "كلمة الكل بيعرفها... إلا واحد!", tags: ["👥 3–20", "📱 تلفون واحد"] },

  { id: "speed", href: "speed.html", sec: "fast", name: "تحدي السرعة", desc: "بلاطة وحدة مختلفة عن الباقي، اضغطها قبل الكمبيوتر", tags: ["👤 ضد الكمبيوتر", "⏱️ ردّة الفعل"], flag: NEW },
  { id: "catch", href: "catch.html", sec: "fast", name: "صيد الكنز", desc: "الذهب بيقع من فوق، اصطده وتجنّب القنابل 💣", tags: ["👤 لحالك", "🏆 نتيجة قياسية"], flag: NEW },
  { id: "anagram", href: "anagram.html", sec: "fast", name: "ركّب الكلمة", desc: "حروف مخلوطة، اكتب الكلمة قبل الكمبيوتر", tags: ["👤 ضد الكمبيوتر", "🔤 كلمات"], flag: NEW },

  { id: "simon", href: "simon.html", sec: "think", name: "تذكّر الألوان", desc: "كل واحد يزيد لون، والباقي لازم يعيد السلسلة من الذاكرة", tags: ["👥 2–4", "📱 تلفون واحد"], flag: NEW },
  { id: "hotcold", href: "hotcold.html", sec: "think", name: "دافئ بارد", desc: "خمّن الرقم المخفي، والتلميح بيقول قد إيش قريب", tags: ["👥 2–4", "📱 تلفون واحد"], flag: NEW },
  { id: "dots", href: "dots.html", sec: "think", name: "نقاط وصناديق", desc: "ارسم خطوط وقفّل الصناديق، والكمبيوتر بيلعب معك", tags: ["👤 ضد الكمبيوتر", "🧩 استراتيجية"], flag: NEW },

  { id: "connect", href: "connect.html", sec: "strat", name: "إكس أو بالجاذبية", desc: "4 قطع بخط واحد... والكمبيوتر بيحاول يمنعك", tags: ["👤 ضد الكمبيوتر", "🎯 3 جولات"], flag: NEW },
  { id: "auction", href: "auction.html", sec: "strat", name: "المزاد", desc: "قيّم السلعة وزايد صح، لا تدفع أكتر من قيمتها", tags: ["👤 ضد 3 تجّار", "💰 أرباح"], flag: NEW },
  { id: "wheel", href: "wheel.html", sec: "strat", name: "عجلة الحظ", desc: "لف العجلة، اختار حروف، وحزّر الجملة قبل الكل", tags: ["👥 2–4", "📱 تلفون واحد"], flag: NEW },

  { id: "pictionary", href: "pictionary.html", sec: "group", name: "ارسم وخمّن", desc: "ارسم الكلمة بدون حروف، وخلّي أصحابك يعرفوها", tags: ["👥 2–5", "📱 تلفون واحد"], flag: NEW },
];

// base: المسار لمجلد الألعاب ("games/" من الرئيسية، "" من صفحة الألعاب)
function gameLocked(id) {
  try { return typeof Rewards !== "undefined" && !!Rewards.tierOf(id) && !Rewards.canPlay((Auth.user() || {}).plan, id); } catch { return false; }
}
// البراند: بدون إيموجي بالواجهة. البيانات بتضل زي ما هي (الفلاتر بتعتمد عليها) وبنشيله وقت العرض
function noEmoji(t) { return String(t).replace(/[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\uFE0F\u200D]+/gu, "").replace(/\s+/g, " ").trim(); }
function gameCard(g, base) {
  const locked = gameLocked(g.id);
  return `<a class="gcard g-${g.id}${locked ? " locked" : ""}" href="${base}${g.href}" data-game="${g.id}">
    <span class="art">${locked ? `<span class="lock"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>بلس</span>` : ""}${g.flag ? `<span class="flag">${noEmoji(g.flag)}</span>` : ""}<img class="pic" src="${base}art/${g.id}.webp" alt="" loading="lazy" decoding="async"></span>
    <span class="body"><b>${g.name}</b><small>${noEmoji(g.desc)}</small><span class="tags">${g.tags.map((t) => `<span>${noEmoji(t)}</span>`).join("")}</span></span>
  </a>`;
}
// ترتيب وتصفية لصفحة الألعاب: sec = "all" أو id قسم، sort = pop | new | solo | group
const GAME_SORTS = [["pop", "الأشهر"], ["new", "الجديد"], ["solo", "لحالك"], ["group", "جماعي"]];
function gamesFiltered(base = "", sec = "all", sort = "pop") {
  let list = GAMES.filter((g) => sec === "all" || g.sec === sec);
  const has = (g, re) => g.tags.some((t) => re.test(t));
  if (sort === "new") list = list.filter((g) => g.flag === NEW || g.flag === "✨ جديد");
  if (sort === "solo") list = list.filter((g) => has(g, /👤|ضد الكمبيوتر|1–|لحالك/));
  if (sort === "group") list = list.filter((g) => has(g, /👥/));
  if (!list.length) return `<div class="card flat"><p class="sub">ما في ألعاب بهالفلتر.</p></div>`;
  return `<div class="games-grid">${list.map((g) => gameCard(g, base)).join("")}</div>`;
}
function gamesGrid(base = "") {
  return SECTIONS.map((sec) => {
    const list = GAMES.filter((g) => g.sec === sec.id);
    if (!list.length) return "";
    return `<section class="gsec"><h2 class="gsec-title">${sec.name}</h2><div class="games-grid">${list.map((g) => gameCard(g, base)).join("")}</div></section>`;
  }).join("");
}

// شريط اللعبة الموحّد: <header class="gbar" data-game="points"></header>
// data-theme-fixed: للألعاب اللي إلها جو ثابت (غامق دايماً) وما بدها زر المظهر.
const GAME_EXTRA = { party: { name: "تحدي الأصحاب", icon: "who" } };
const BACK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
function mountGameBar() {
  document.querySelectorAll(".gbar[data-game]").forEach((bar) => {
    const id = bar.dataset.game, g = GAMES.find((x) => x.id === id) || GAME_EXTRA[id] || { name: document.title };
    const icon = GAME_ICON[g.icon || id] || "";
    const themed = !bar.hasAttribute("data-theme-fixed") && typeof themeToggle === "function";
    // RTL: زر الرجوع بالبداية (يمين)، بعده اسم اللعبة، وزر المظهر بالآخر
    bar.innerHTML = `<span class="gs"><a class="gback" href="./" id="gback" aria-label="رجوع للألعاب" title="الألعاب">${BACK_ICON}</a>
      <a class="gt" href="./"><span class="chip g-${g.icon || id}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">${icon}</svg></span><b>${g.name}</b></a></span>
      ${themed ? themeToggle() : ""}`;
    // إذا في لعبة شغّالة وما بتنحفظ، الصفحة بتعرّف leaveGuard() وبنسأل قبل ما نطلع
    bar.querySelectorAll('a[href="./"]').forEach((a) => a.addEventListener("click", (e) => {
      const msg = typeof window.leaveGuard === "function" && window.leaveGuard();
      if (msg && !confirm(msg)) e.preventDefault();
    }));
  });
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountGameBar); else mountGameBar();
// «طريقة اللعب»: مفتوحة لأول زيارة بس
document.addEventListener("toggle", (e) => {
  const d = e.target; if (!(d instanceof HTMLDetailsElement) || !d.classList.contains("howto") || !d.dataset.key) return;
  try { localStorage.setItem("howto-" + d.dataset.key, d.open ? "open" : "closed"); } catch {}
}, true);
function howto(key, inner, title = "📖 طريقة اللعب") {
  let st = null; try { st = localStorage.getItem("howto-" + key); } catch {}
  return `<details class="howto" data-key="${key}" ${st === "closed" ? "" : "open"}><summary>${title}</summary><div class="howto-body">${inner}</div></details>`;
}
