// صوت «ملك السهرة»: موسيقى ومؤثرات مولّدة بالكود (WebAudio)، بدون ملفات.
// الموسيقى 3 أجواء: lobby (هادية)، play (حماس)، tense (توتر وقت الجواب والقنبلة).
"use strict";
const Sound = (() => {
  let ac = null, master = null, music = null, noiseBuf = null;
  let musicOn = true, mood = null, loop = null, step = 0, nextT = 0;

  function ctx() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ac = new AC();
      master = ac.createGain(); master.gain.value = 0.9; master.connect(ac.destination);
      music = ac.createGain(); music.gain.value = 0.55; music.connect(master);
      noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ac.state === "suspended") ac.resume().catch(() => {});
    return ac;
  }
  // نغمة: تردد، وقت البداية، المدة، الشكل، العلو، وتردد النهاية (للانزلاق)
  function tone(f, t, dur, type = "sine", vol = 0.1, dest = master, to = null) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t);
    if (to) o.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest); o.start(t); o.stop(t + dur + 0.03);
  }
  // خشّة (للطبلة والجمهور والانفجار)
  function noise(t, dur, vol, type = "highpass", freq = 6000, dest = master, swell = false) {
    const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = noiseBuf; s.loop = true; f.type = type; f.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t);
    if (swell) { g.gain.exponentialRampToValueAtTime(vol, t + dur * 0.3); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); }
    else { g.gain.exponentialRampToValueAtTime(vol, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); }
    s.connect(f); f.connect(g); g.connect(dest); s.start(t); s.stop(t + dur + 0.05);
  }

  // كل جو: 16 خطوة. الباص واللحن ترددات (0 = سكوت)، والإيقاع 1/0.
  const _ = 0;
  const MOODS = {
    lobby: { bpm: 96, bass: [110, _, _, _, _, _, 110, _, 131, _, _, _, _, _, 98, _], lead: [440, _, 523, _, 659, _, 523, _, 392, _, 494, _, 587, _, 494, _], kick: [1, _, _, _, _, _, _, _, 1, _, _, _, _, _, _, _], hat: [_, _, 1, _, _, _, 1, _, _, _, 1, _, _, _, 1, _], clap: [], leadType: "triangle", leadVol: 0.035 },
    play: { bpm: 118, bass: [110, _, 110, _, _, 110, _, _, 131, _, 131, _, _, 98, _, 98], lead: [659, _, _, 523, _, _, 440, _, 587, _, _, 494, _, _, 392, 440], kick: [1, _, _, _, 1, _, _, _, 1, _, _, _, 1, _, _, _], hat: [_, _, 1, _, _, _, 1, _, _, _, 1, _, _, _, 1, 1], clap: [_, _, _, _, 1, _, _, _, _, _, _, _, 1, _, _, _], leadType: "square", leadVol: 0.022 },
    tense: { bpm: 134, bass: [55, 55, _, 55, 55, _, 55, _, 58, 58, _, 58, 58, _, 58, _], lead: [220, _, 233, _, 220, _, 233, _, 247, _, 262, _, 247, _, 277, _], kick: [1, _, _, 1, _, _, _, _, 1, _, _, 1, _, _, _, _], hat: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], clap: [], leadType: "sawtooth", leadVol: 0.02 },
  };
  function schedule(m, i, t) {
    const spb = 60 / m.bpm / 4;
    if (m.kick[i]) tone(120, t, 0.16, "sine", 0.3, music, 38);
    if (m.hat[i]) noise(t, 0.03, m === MOODS.tense ? 0.035 : 0.05, "highpass", 8000, music);
    if (m.clap[i]) noise(t, 0.09, 0.12, "bandpass", 1800, music);
    if (m.bass[i]) tone(m.bass[i], t, spb * 1.8, "triangle", 0.16, music);
    if (m.lead[i]) tone(m.lead[i], t, spb * 1.6, m.leadType, m.leadVol, music);
  }
  function run() {
    clearInterval(loop); loop = null;
    if (!musicOn || !mood || !ctx()) return;
    step = 0; nextT = ac.currentTime + 0.06;
    loop = setInterval(() => {
      const m = MOODS[mood];
      if (!m) return;
      while (nextT < ac.currentTime + 0.14) { schedule(m, step, nextT); nextT += 60 / m.bpm / 4; step = (step + 1) % 16; }
    }, 30);
  }

  const FX = {
    ding: (t) => { tone(988, t, 0.25, "sine", 0.12); tone(1318, t + 0.1, 0.3, "sine", 0.1); },
    ok: (t) => { tone(880, t, 0.1, "triangle", 0.12); tone(1320, t + 0.08, 0.18, "triangle", 0.12); },
    bad: (t) => { tone(196, t, 0.3, "sawtooth", 0.1, master, 110); },
    tick: (t) => tone(1500, t, 0.04, "square", 0.05),
    heart: (t) => { tone(70, t, 0.12, "sine", 0.35, master, 45); tone(70, t + 0.2, 0.12, "sine", 0.25, master, 45); },
    pass: (t) => tone(520, t, 0.08, "square", 0.06, master, 760),
    join: (t) => tone(700, t, 0.1, "triangle", 0.1),
    stage: (t) => [523, 659, 784, 1046].forEach((f, i) => tone(f, t + i * 0.13, 0.28, "triangle", 0.12)),
    gold: (t) => [784, 988, 1175, 1568, 1175, 1568].forEach((f, i) => tone(f, t + i * 0.09, 0.2, "square", 0.05)),
    final: (t) => { [523, 659, 784, 1046, 1318, 1568].forEach((f, i) => tone(f, t + i * 0.15, 0.4, "triangle", 0.13)); noise(t + 0.9, 2.4, 0.22, "bandpass", 1100, master, true); },
    // طبلة التشويق قبل كشف الجواب
    drum: (t) => { for (let i = 0; i < 20; i++) noise(t + i * 0.065, 0.05, 0.03 + i * 0.006, "bandpass", 1400); noise(t + 1.35, 0.7, 0.16, "highpass", 5000); tone(784, t + 1.35, 0.4, "triangle", 0.12); },
    whistle: (t) => { for (const [at, d] of [[0, 0.18], [0.26, 0.5]]) { tone(2350, t + at, d, "square", 0.05); tone(2480, t + at, d, "sine", 0.07); } },
    crowd: (t) => { noise(t, 2.2, 0.3, "bandpass", 900, master, true); noise(t, 2.2, 0.12, "bandpass", 2400, master, true); },
    boom: (t) => { noise(t, 1.1, 0.5, "lowpass", 500); tone(140, t, 0.9, "sine", 0.5, master, 28); },
  };

  return {
    // أول لمسة عالشاشة بتفتح الصوت (قيود المتصفح)
    unlock() { if (ctx() && musicOn && mood && !loop) run(); },
    fx(name, delay = 0) { if (!ctx() || !FX[name]) return; try { FX[name](ac.currentTime + delay); } catch {} },
    mood(m) { if (m === mood) return; mood = m; run(); },
    setMusic(v) { if (v === musicOn) return; musicOn = v; run(); },
    get musicOn() { return musicOn; },
  };
})();
document.addEventListener("pointerdown", () => Sound.unlock(), { passive: true });
