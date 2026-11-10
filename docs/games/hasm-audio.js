// صوت «ليلة الحسم»: كله مولّد بالكود (WebAudio)، بدون ملفات.
// الموسيقى 4 أجواء: anthem (النشيد)، pick (توتر الاختيار)، show (طبول المدرجات)، champ (التتويج).
"use strict";
const HasmSound = (() => {
  let ac = null, master = null, music = null, bed = null, noiseBuf = null;
  let musicOn = true, mood = null, loop = null, step = 0, nextT = 0;

  function ctx() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ac = new AC();
      master = ac.createGain(); master.gain.value = 0.9; master.connect(ac.destination);
      music = ac.createGain(); music.gain.value = 0.5; music.connect(master);
      noiseBuf = ac.createBuffer(1, ac.sampleRate * 2, ac.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      // هدير الجمهور: خشّة مفلترة شغّالة على طول، وبنعلّيها وقت الهجمة
      const s = ac.createBufferSource(), f = ac.createBiquadFilter();
      s.buffer = noiseBuf; s.loop = true; f.type = "bandpass"; f.frequency.value = 700; f.Q.value = 0.6;
      bed = ac.createGain(); bed.gain.value = 0;
      s.connect(f); f.connect(bed); bed.connect(master); s.start();
    }
    if (ac.state === "suspended") ac.resume().catch(() => {});
    return ac;
  }
  function tone(f, t, dur, type = "sine", vol = 0.1, dest = master, to = null, attack = 0.012) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t);
    if (to) o.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest); o.start(t); o.stop(t + dur + 0.03);
  }
  function noise(t, dur, vol, type = "highpass", freq = 6000, dest = master, swell = 0) {
    const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = noiseBuf; s.loop = true; f.type = type; f.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + (swell ? dur * swell : 0.005)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(dest); s.start(t); s.stop(t + dur + 0.05);
  }
  // نحاسيات: موجتين منشار مع فلتر، للنشيد والبوق
  function brass(f, t, dur, vol, dest = music) {
    const flt = ac.createBiquadFilter(), g = ac.createGain();
    flt.type = "lowpass"; flt.frequency.setValueAtTime(500, t); flt.frequency.linearRampToValueAtTime(2200, t + 0.08); flt.frequency.linearRampToValueAtTime(900, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.04); g.gain.setValueAtTime(vol, t + dur * 0.7); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    [1, 1.006].forEach((m) => { const o = ac.createOscillator(); o.type = "sawtooth"; o.frequency.value = f * m; o.connect(flt); o.start(t); o.stop(t + dur + 0.05); });
    flt.connect(g); g.connect(dest);
  }
  const N = (n) => 440 * Math.pow(2, (n - 69) / 12);   // رقم MIDI ← تردد

  // كل جو: خطوات، سرعة، ودالة بتعزف الخطوة i بالوقت t
  const MOODS = {
    // نشيد أصلي: ري مينور، نحاسيات وتيمباني
    anthem: { bpm: 84, steps: 32, play(i, t, sp) {
      const chords = [[50, 57, 62, 65], [46, 53, 58, 62], [48, 55, 60, 64], [45, 52, 57, 61]];
      const mel = [74, 0, 0, 72, 74, 0, 77, 0, 74, 0, 0, 70, 72, 0, 74, 0, 76, 0, 0, 74, 76, 0, 79, 0, 81, 0, 79, 0, 76, 0, 73, 0];
      if (i % 8 === 0) { chords[i / 8].forEach((n) => brass(N(n), t, sp * 7.6, 0.035)); tone(N(chords[i / 8][0] - 12), t, sp * 7, "triangle", 0.12, music); }
      if (mel[i]) brass(N(mel[i]), t, sp * 1.9, 0.06);
      if (i % 8 === 0 || i % 8 === 6) { tone(82, t, 0.5, "sine", 0.22, music, 48); noise(t, 0.2, 0.05, "lowpass", 300, music); }
      if (i % 4 === 2) noise(t, 0.09, 0.02, "highpass", 5000, music);
    } },
    // توتر: دقّات قلب، نغمة واطية، وتكتكة
    pick: { bpm: 104, steps: 16, play(i, t, sp) {
      if (i % 8 === 0 || i % 8 === 2) tone(60, t, 0.22, "sine", 0.3, music, 38);
      if (i % 4 === 0) tone(N(38), t, sp * 3.6, "sawtooth", 0.035, music);
      if (i % 2 === 1) noise(t, 0.03, 0.022, "highpass", 8000, music);
      const arp = [62, 0, 65, 0, 0, 62, 0, 68, 0, 0, 65, 0, 63, 0, 0, 0][i];
      if (arp) tone(N(arp), t, sp * 0.9, "triangle", 0.05, music);
    } },
    // طبول المدرجات وباص راكض
    show: { bpm: 126, steps: 16, play(i, t, sp) {
      const kick = [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0][i], clap = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1][i];
      const bass = [38, 0, 38, 0, 0, 38, 0, 41, 0, 41, 0, 0, 36, 0, 36, 43][i];
      const lead = [0, 0, 69, 0, 0, 0, 72, 0, 74, 0, 0, 72, 0, 0, 69, 0][i];
      if (kick) { tone(120, t, 0.26, "sine", 0.34, music, 44); noise(t, 0.05, 0.05, "lowpass", 400, music); }
      if (clap) { noise(t, 0.12, 0.11, "bandpass", 1600, music); noise(t + 0.012, 0.1, 0.07, "bandpass", 2200, music); }
      if (i % 2 === 0) noise(t, 0.035, 0.02, "highpass", 9000, music);
      if (bass) tone(N(bass), t, sp * 1.5, "sawtooth", 0.07, music);
      if (lead) tone(N(lead), t, sp * 1.6, "square", 0.028, music);
    } },
    // التتويج: فا ميجور، فرح
    champ: { bpm: 112, steps: 32, play(i, t, sp) {
      const chords = [[53, 57, 60], [58, 62, 65], [48, 52, 55], [53, 57, 60]];
      const mel = [77, 0, 77, 79, 81, 0, 84, 0, 82, 0, 82, 81, 79, 0, 77, 0, 79, 0, 79, 81, 82, 0, 79, 0, 81, 0, 84, 0, 89, 0, 0, 0];
      if (i % 8 === 0) { chords[i / 8].forEach((n) => brass(N(n), t, sp * 7.5, 0.04)); tone(N(chords[i / 8][0] - 12), t, sp * 7, "triangle", 0.12, music); }
      if (mel[i]) brass(N(mel[i]), t, sp * 1.7, 0.065);
      if (i % 4 === 0) { tone(110, t, 0.22, "sine", 0.26, music, 46); }
      if (i % 4 === 2) noise(t, 0.1, 0.07, "bandpass", 1800, music);
      if (i % 2 === 1) noise(t, 0.03, 0.02, "highpass", 9000, music);
    } },
  };
  function tick() {
    if (!ac || !mood || !musicOn) return;
    const m = MOODS[mood], sp = 60 / m.bpm / 4;
    while (nextT < ac.currentTime + 0.25) { m.play(step % m.steps, nextT, sp); step++; nextT += sp; }
  }
  function stop() { clearInterval(loop); loop = null; }
  function start() {
    stop();
    if (!mood || !musicOn || !ctx()) return;
    step = 0; nextT = ac.currentTime + 0.06;
    loop = setInterval(tick, 80); tick();
  }

  const FX = {
    tick: (t) => tone(1000, t, 0.04, "square", 0.04),
    tap: (t) => tone(520, t, 0.06, "triangle", 0.09, master, 760),
    ok: (t) => { tone(660, t, 0.1, "triangle", 0.12); tone(990, t + 0.09, 0.2, "triangle", 0.12); },
    bad: (t) => { tone(300, t, 0.16, "sawtooth", 0.08, master, 180); tone(190, t + 0.14, 0.3, "sawtooth", 0.08, master, 110); },
    flip: (t) => noise(t, 0.16, 0.1, "bandpass", 3200, master, 0.5),
    coin: (t) => { tone(1320, t, 0.08, "square", 0.05); tone(1760, t + 0.07, 0.25, "square", 0.05); },
    gavel: (t) => [0, 0.2].forEach((d) => { noise(t + d, 0.06, 0.3, "bandpass", 900); tone(170, t + d, 0.12, "sine", 0.3, master, 90); }),
    roll: (t, dur = 1.2) => { for (let x = 0; x < dur; x += 0.055) noise(t + x, 0.05, 0.05 + 0.1 * (x / dur), "bandpass", 420); },
    whistle: (t, long) => {
      const dur = long ? 0.95 : 0.4;
      [2350, 2480].forEach((f) => {
        const o = ac.createOscillator(), g = ac.createGain(), l = ac.createOscillator(), lg = ac.createGain();
        o.type = "sine"; o.frequency.value = f; l.frequency.value = 38; lg.gain.value = 55; l.connect(lg); lg.connect(o.frequency);
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.11, t + 0.02); g.gain.setValueAtTime(0.11, t + dur - 0.06); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        o.connect(g); g.connect(master); o.start(t); l.start(t); o.stop(t + dur + 0.05); l.stop(t + dur + 0.05);
      });
    },
    kick: (t) => { tone(190, t, 0.12, "sine", 0.3, master, 60); noise(t, 0.05, 0.12, "lowpass", 1400); },
    pass: (t) => { tone(260, t, 0.05, "sine", 0.14, master, 120); noise(t, 0.03, 0.05, "lowpass", 2000); },
    goal: (t) => {
      [220, 277, 330, 440].forEach((f) => brass(f, t, 1.5, 0.07, master));
      noise(t, 3.4, 0.4, "bandpass", 850, master, 0.12); noise(t, 3, 0.16, "bandpass", 2300, master, 0.15);
      [72, 76, 79, 84].forEach((n, i) => tone(N(n), t + 0.5 + i * 0.11, 0.34, "triangle", 0.1));
    },
    ooh: (t) => { noise(t, 1.5, 0.26, "bandpass", 600, master, 0.2); tone(330, t, 0.9, "sawtooth", 0.035, master, 150, 0.15); },
    post: (t) => { tone(1850, t, 0.5, "sine", 0.13); tone(2770, t, 0.34, "sine", 0.07); tone(140, t, 0.1, "sine", 0.24, master, 70); },
    save: (t) => { noise(t, 0.09, 0.26, "lowpass", 900); tone(150, t, 0.14, "sine", 0.26, master, 70); },
    flag: (t) => { FX.whistle(t); tone(420, t + 0.42, 0.3, "sawtooth", 0.05, master, 260); },
    red: (t) => { FX.whistle(t, true); tone(130, t + 0.2, 0.5, "sawtooth", 0.1, master, 95); },
    var: (t) => [0, 0.2, 0.4].forEach((d, i) => tone(i === 2 ? 1175 : 880, t + d, 0.11, "square", 0.07)),
    magic: (t) => [84, 88, 91, 96, 100].forEach((n, i) => tone(N(n), t + i * 0.06, 0.3, "sine", 0.07)),
    news: (t) => { [0, 0.14, 0.28].forEach((d) => tone(N(81), t + d, 0.09, "square", 0.06)); tone(N(86), t + 0.42, 0.4, "square", 0.06); },
    sold: (t) => { FX.gavel(t); [76, 79, 84].forEach((n, i) => tone(N(n), t + 0.42 + i * 0.09, 0.3, "triangle", 0.1)); },
    champ: (t) => { [65, 69, 72, 77].forEach((n, i) => brass(N(n), t + i * 0.16, 0.5, 0.08, master)); brass(N(81), t + 0.66, 1.3, 0.1, master); noise(t + 0.5, 4, 0.34, "bandpass", 900, master, 0.15); },
  };

  return {
    setMusic(on) { musicOn = !!on; if (!musicOn) { stop(); if (bed && ac) bed.gain.setTargetAtTime(0, ac.currentTime, 0.1); } else if (mood && !loop) start(); },
    mood(m) { if (m === mood && (loop || !musicOn)) return; mood = MOODS[m] ? m : null; start(); },
    fx(k, arg) { if (!musicOn || !FX[k] || !ctx()) return; try { FX[k](ac.currentTime + 0.01, arg); } catch {} },
    // مستوى هدير الجمهور من 0 لـ1
    crowd(v) { if (!ac || !bed) return; bed.gain.setTargetAtTime(musicOn ? Math.max(0, Math.min(1, v)) * 0.16 : 0, ac.currentTime, 0.25); },
    unlock() { ctx(); if (mood && musicOn && !loop) start(); },
  };
})();
