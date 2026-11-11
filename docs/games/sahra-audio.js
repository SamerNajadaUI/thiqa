// صوت «ملك السهرة»: كله مولّد بالكود (WebAudio)، بدون ملفات.
// جو مدرّج: طبلة (دُم/تَك)، تصفيق، هدير جمهور، صافرة، بوق. الموسيقى مقام حجاز على ري وإيقاعها هو البطل.
"use strict";
const Sound = (() => {
  let ac = null, master = null, music = null, soft = null, noiseBuf = null;
  let musicOn = true, mood = null, loop = null, step = 0, nextT = 0;
  const jit = () => 1 + (Math.random() - 0.5) * 0.06;   // كل مؤثر بيطلع شوي مختلف، عشان ما يزهّق

  function ctx() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ac = new AC();
      const comp = ac.createDynamicsCompressor();
      comp.threshold.value = -16; comp.ratio.value = 5; comp.attack.value = 0.004; comp.release.value = 0.2;
      comp.connect(ac.destination);
      master = ac.createGain(); master.gain.value = 0.95; master.connect(comp);
      music = ac.createGain(); music.gain.value = 0.3; music.connect(master);
      soft = ac.createBiquadFilter(); soft.type = "lowpass"; soft.frequency.value = 3000; soft.connect(master);   // الموجات الحادة بتمر من هون
      noiseBuf = ac.createBuffer(1, ac.sampleRate * 2, ac.sampleRate);
      const d = noiseBuf.getChannelData(0);
      let last = 0;
      for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; last = (last + 0.04 * w) / 1.04; d[i] = w * 0.5 + last * 6; }   // أبيض + شوية بنّي = أدفى
    }
    if (ac.state === "suspended") ac.resume().catch(() => {});
    return ac;
  }
  function tone(f, t, dur, type = "sine", vol = 0.1, dest = null, to = null, att = 0.012) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t);
    if (to) o.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + att); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest || (type === "square" || type === "sawtooth" ? soft : master)); o.start(t); o.stop(t + dur + 0.03);
    return o;
  }
  function noise(t, dur, vol, type = "highpass", freq = 6000, dest = master, shape = "hit", q = 0.8, sweep = null) {
    const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = noiseBuf; s.loop = true; f.type = type; f.frequency.setValueAtTime(freq, t); f.Q.value = q;
    if (sweep) f.frequency.exponentialRampToValueAtTime(sweep, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    if (shape === "swell") { g.gain.exponentialRampToValueAtTime(vol, t + dur * 0.25); g.gain.setValueAtTime(vol, t + dur * 0.55); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); }
    else if (shape === "rise") { g.gain.exponentialRampToValueAtTime(vol, t + dur * 0.92); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); }
    else { g.gain.exponentialRampToValueAtTime(vol, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); }
    s.connect(f); f.connect(g); g.connect(dest); s.start(t, Math.random()); s.stop(t + dur + 0.05);
    return g;
  }
  // ----- آلات المدرّج -----
  const dum = (t, v = 0.5, dest = master) => { tone(150 * jit(), t, 0.2, "sine", v, dest, 55, 0.004); noise(t, 0.012, v * 0.25, "lowpass", 900, dest); };
  const tak = (t, v = 0.2, dest = master) => { noise(t, 0.05, v, "highpass", 3200, dest); tone(820 * jit(), t, 0.045, "triangle", v * 0.5, dest, null, 0.003); };
  const clap = (t, v = 0.2, dest = master) => { for (let i = 0; i < 4; i++) noise(t + i * 0.011, 0.11, v * (i === 3 ? 1 : 0.6), "bandpass", 1500 * jit(), dest, "hit", 1.2); };
  // هدير الجمهور: 3 طبقات خشّة، وبتتنفّس
  function crowd(t, dur = 2.6, vol = 0.34) {
    for (const [f, q, v] of [[520, 0.7, 1], [1250, 1, 0.6], [2600, 2, 0.3]]) {
      const g = noise(t, dur, vol * v, "bandpass", f, master, "swell", q);
      const l = ac.createOscillator(), lg = ac.createGain();
      l.frequency.value = 4 + Math.random() * 3; lg.gain.value = vol * v * 0.25; l.connect(lg); lg.connect(g.gain); l.start(t); l.stop(t + dur);
    }
  }
  // «أووووه»: الفرصة الضايعة
  function ooh(t, vol = 0.07) {
    const f1 = ac.createBiquadFilter(), g = ac.createGain();
    f1.type = "bandpass"; f1.frequency.value = 800; f1.Q.value = 1.4; f1.connect(g); g.connect(master);
    g.gain.setValueAtTime(1, t);
    for (let i = 0; i < 5; i++) { const o = tone(330 * (1 + (i - 2) * 0.012), t, 0.95, "sawtooth", vol, f1, 190 * (1 + (i - 2) * 0.012), 0.08); o.detune.value = (i - 2) * 9; }
    noise(t, 0.9, 0.08, "bandpass", 900, master, "swell", 0.8);
  }
  function whistle(t, dur = 0.35, vol = 0.07) {
    for (const f of [2800, 2950]) {
      const o = tone(f, t, dur, "square", vol, master, null, 0.005);
      const l = ac.createOscillator(), lg = ac.createGain();
      l.frequency.value = 36; lg.gain.value = 70; l.connect(lg); lg.connect(o.frequency); l.start(t); l.stop(t + dur + 0.05);
    }
    noise(t, dur, vol * 0.5, "bandpass", 2900, master, "swell", 6);
  }
  const horn = (t, dur = 1.5, vol = 0.07, notes = [233, 349, 466]) => notes.forEach((f) => { tone(f, t, dur, "sawtooth", vol, soft, null, 0.05); tone(f * 1.006, t, dur, "sawtooth", vol * 0.7, soft, null, 0.05); });
  function duck(sec) { if (!music) return; const t = ac.currentTime; music.gain.cancelScheduledValues(t); music.gain.setValueAtTime(music.gain.value, t); music.gain.linearRampToValueAtTime(0.02, t + 0.06); music.gain.setValueAtTime(0.02, t + sec); music.gain.linearRampToValueAtTime(0.3, t + sec + 0.8); }

  // ----- الموسيقى: حجاز على ري. 64 خطوة (4 بارات): الإيقاع بيلف كل 16، واللحن جمل قصيرة وبعدها سكوت -----
  const _ = 0, D = 293.7, Eb = 311.1, Fs = 370, G = 392, A = 440, Bb = 466.2, C5 = 523.3, D5 = 587.3;
  const MOODS = {
    lobby: { bpm: 92, dum: [1, _, _, _, _, _, _, _, 1, _, 1, _, _, _, _, _], tak: [_, _, _, _, 1, _, _, 1, _, _, _, _, 1, _, _, _], clap: [],
      bass: [73.4, _, _, _, _, _, _, _, 73.4, _, _, _, 98, _, 110, _],
      lead: [D, _, _, Eb, Fs, _, _, _, G, _, Fs, _, Eb, _, D, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, A, _, _, G, Fs, _, _, _, G, _, A, _, Bb, _, A, _], type: "triangle", vol: 0.05 },
    play: { bpm: 108, dum: [1, _, _, 1, _, _, 1, _, 1, _, _, _, _, _, 1, _], tak: [_, _, 1, _, 1, _, _, 1, _, _, 1, _, 1, _, _, 1], clap: [_, _, _, _, 1, _, _, _, _, _, _, _, 1, _, _, _],
      bass: [73.4, _, _, 73.4, _, _, 73.4, _, 98, _, _, 98, _, _, 110, _],
      lead: [D5, _, C5, _, Bb, _, A, _, _, _, A, Bb, A, _, G, _, Fs, _, _, _, G, _, A, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, A, _, Bb, _, C5, _, D5, _, _, _, C5, Bb, A, _, _, _], type: "triangle", vol: 0.045 },
    tense: { bpm: 124, dum: [1, _, _, _, 1, _, _, _, 1, _, _, _, 1, _, 1, _], tak: [_, _, _, _, _, _, 1, _, _, _, _, _, _, _, _, 1], clap: [],
      bass: [73.4, _, 73.4, _, _, _, 73.4, _, 77.8, _, 77.8, _, _, _, 77.8, _],
      lead: [D, _, _, _, Eb, _, _, _, D, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _], type: "sine", vol: 0.04 },
  };
  function schedule(m, i, t) {
    const spb = 60 / m.bpm / 4, r = i % 16, fill = i >= 56 && i % 2 === 0;   // فِلّة طبلة آخر نص بار
    if (m.dum[r]) dum(t, 0.42, music);
    if (m.tak[r] || (fill && m !== MOODS.lobby)) tak(t, fill ? 0.12 + (i - 56) * 0.012 : 0.16, music);
    if (m.clap[r]) clap(t, 0.13, music);
    if (m.bass[r]) { tone(m.bass[r], t, spb * 2.2, "triangle", 0.22, music); tone(m.bass[r] * 2, t, spb * 1.6, "sine", 0.1, music); }
    const n = m.lead[i % m.lead.length];
    if (n) { tone(n, t, spb * 2.4, m.type, m.vol, music); tone(n * 2, t, spb * 1.2, "sine", m.vol * 0.3, music); }
  }
  function run() {
    clearInterval(loop); loop = null;
    if (!musicOn || !mood || !ctx()) return;
    step = 0; nextT = ac.currentTime + 0.06;
    loop = setInterval(() => {
      const m = MOODS[mood];
      if (!m) return;
      if (nextT < ac.currentTime - 0.5) nextT = ac.currentTime + 0.05;   // رجعنا من الخلفية
      while (nextT < ac.currentTime + 0.14) { schedule(m, step, nextT); nextT += 60 / m.bpm / 4; step = (step + 1) % 64; }
    }, 30);
  }

  const FX = {
    ding: (t) => { tone(988 * jit(), t, 0.25, "sine", 0.12); tone(1318, t + 0.1, 0.3, "sine", 0.1); },
    ok: (t) => { tone(880, t, 0.1, "triangle", 0.14); tone(1320, t + 0.08, 0.2, "triangle", 0.14); tone(1760, t + 0.16, 0.35, "sine", 0.08); },
    bad: (t) => { tone(196, t, 0.32, "sawtooth", 0.12, soft, 98); tone(60, t, 0.2, "sine", 0.3, master, 40); },
    tick: (t) => tak(t, 0.1),
    heart: (t) => { tone(70, t, 0.13, "sine", 0.5, master, 45, 0.005); tone(70, t + 0.2, 0.13, "sine", 0.35, master, 45, 0.005); },
    pass: (t) => { tone(520 * jit(), t, 0.09, "triangle", 0.1, master, 780); tak(t + 0.05, 0.08); },
    join: (t) => { tak(t, 0.14); tone(700, t + 0.04, 0.12, "triangle", 0.1); },
    wipe: (t) => noise(t, 0.34, 0.2, "bandpass", 400, master, "rise", 0.9, 5000),
    // فاصل المرحلة: مسحة + دُم دُم تَك + نفخة نحاس
    stage: (t) => { FX.wipe(t); dum(t + 0.28, 0.6); dum(t + 0.46, 0.6); tak(t + 0.64, 0.3); clap(t + 0.64, 0.2); horn(t + 0.64, 0.7, 0.05, [293.7, 370, 440]); },
    gold: (t) => [784, 988, 1175, 1568, 1175, 1568, 2350].forEach((f, i) => tone(f, t + i * 0.08, 0.22, "triangle", 0.07)),
    // طبلة التشويق: بتسرع وبتعلى لحد الكشف. sec طولها
    drum: (t, sec = 1.4) => { let x = 0, gap = 0.13, i = 0; while (x < sec - 0.08) { (i % 2 ? tak : dum)(t + x, 0.12 + (x / sec) * 0.3); x += gap; gap = Math.max(0.045, gap * 0.93); i++; } clap(t + sec, 0.3); tone(784, t + sec, 0.4, "triangle", 0.1); },
    whistle: (t) => { whistle(t, 0.16); whistle(t + 0.24, 0.5); },
    whistle3: (t) => { whistle(t, 0.3); whistle(t + 0.42, 0.3); whistle(t + 0.84, 0.9); },
    crowd: (t, sec = 2.2) => crowd(t, sec, 0.3),
    cheer: (t) => { crowd(t, 1.2, 0.18); clap(t + 0.05, 0.16); },
    ooh: (t) => ooh(t),
    kick: (t) => { tone(180, t, 0.12, "sine", 0.6, master, 60, 0.003); noise(t, 0.04, 0.25, "lowpass", 1400); },
    net: (t) => noise(t, 0.28, 0.2, "bandpass", 5200, master, "hit", 0.6, 1800),
    // الجول: سكتة قصيرة، وبعدين كل إشي مع بعض
    goal: (t) => { duck(3); const s = t + 0.12; FX.net(s - 0.1); tone(140, s, 0.8, "sine", 0.6, master, 32, 0.004); crowd(s, 3.2, 0.42); horn(s + 0.05, 1.7, 0.08); [0, 0.18, 0.36, 0.45, 0.54].forEach((d) => clap(s + 0.9 + d, 0.2)); },
    save: (t) => { tone(110, t, 0.22, "sine", 0.6, master, 50, 0.003); noise(t, 0.08, 0.3, "lowpass", 700); ooh(t + 0.08); },
    post: (t) => { tone(1180 * jit(), t, 0.5, "triangle", 0.22, master, null, 0.002); tone(2390, t, 0.3, "sine", 0.1, master, null, 0.002); },
    var: (t, sec = 2) => { for (let x = 0; x < sec - 0.2; x += 0.42) { tone(1250, t + x, 0.07, "sine", 0.07); tone(1250, t + x + 0.11, 0.07, "sine", 0.05); } tone(98, t, sec, "triangle", 0.06); },
    fire: (t) => { noise(t, 0.5, 0.25, "bandpass", 500, master, "rise", 0.8, 4200); [0, 0.2, 0.4, 0.5, 0.6].forEach((d, i) => dum(t + 0.45 + d, 0.5 + i * 0.03)); horn(t + 1.05, 0.5, 0.05, [293.7, 440, 587.3]); },
    fizz: (t) => noise(t, 0.4, 0.14, "highpass", 5000, master, "hit", 0.7, 1200),
    lead: (t) => { horn(t, 0.22, 0.06, [392, 494]); horn(t + 0.24, 0.7, 0.07, [466, 587, 698]); crowd(t + 0.2, 1.6, 0.22); },
    remo: (t) => { [0, 0.15, 0.3].forEach((d) => dum(t + d, 0.5)); horn(t + 0.45, 0.6, 0.06, [233, 293.7, 349]); },
    boom: (t) => { duck(1.6); noise(t, 1.3, 0.7, "lowpass", 600, master, "hit", 0.7, 80); tone(140, t, 1, "sine", 0.7, master, 26, 0.003); noise(t, 0.2, 0.3, "highpass", 3000); ooh(t + 0.35); },
    // عدّاد النقاط: تكّات بتطلع، وآخرها جرس
    count: (t, n = 8) => { for (let i = 0; i < n; i++) tone(600 * Math.pow(1.045, i), t + i * 0.055, 0.035, "triangle", 0.07); tone(1320, t + n * 0.055, 0.6, "sine", 0.1); tone(1980, t + n * 0.055, 0.6, "sine", 0.05); },
    finalcall: (t) => { duck(2.4); [0, 0.5, 1].forEach((d) => FX.heart(t + d)); horn(t + 1.5, 0.9, 0.07, [146.8, 220, 293.7]); crowd(t + 1.4, 2, 0.25); },
    // التتويج: لحن نصر + جمهور طويل + تصفيق المدرّج
    final: (t) => { duck(5); const mel = [[392, 0.18], [392, 0.18], [392, 0.18], [523, 0.5], [466, 0.18], [523, 0.18], [587, 0.9]]; let x = 0; for (const [f, d] of mel) { horn(t + x, d + 0.08, 0.07, [f, f * 1.5, f * 2]); x += d + 0.03; } crowd(t + 0.4, 5, 0.4); for (let b = 0; b < 3; b++) [0, 0.22, 0.44, 0.55, 0.66].forEach((d) => clap(t + 2.4 + b * 0.95 + d, 0.2)); dum(t + 0.75, 0.7); },
  };

  document.addEventListener("visibilitychange", () => { if (!document.hidden && ac && ac.state === "suspended") ac.resume().catch(() => {}); });
  return {
    unlock() { if (ctx() && musicOn && mood && !loop) run(); },
    fx(name, delay = 0, arg) { if (!ctx() || !FX[name]) return; try { FX[name](ac.currentTime + delay, arg); } catch {} },
    mood(m) { if (m === mood) return; mood = m; run(); },
    setMusic(v) { if (v === musicOn) return; musicOn = v; run(); },
    get musicOn() { return musicOn; },
  };
})();
document.addEventListener("pointerdown", () => Sound.unlock(), { passive: true });
