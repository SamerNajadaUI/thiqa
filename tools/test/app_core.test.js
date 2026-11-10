// فحص منطق التطبيق الصافي: مستوى، مضاعف، سقف يومي، قفل الألعاب، رقم أردني.
const test = require("node:test"), assert = require("node:assert/strict");
const { Rewards: R, Auth: A } = require("../../docs/app/core.js");

test("المستوى: حدود 0/50/200 ونسبة التقدم", () => {
  assert.equal(R.levelInfo(0).level, 1);
  assert.equal(R.levelInfo(49).level, 1);
  assert.equal(R.levelInfo(50).level, 2);
  assert.equal(R.levelInfo(199).level, 2);
  assert.equal(R.levelInfo(200).level, 3);
  const i = R.levelInfo(125); // بين 50 و 200
  assert.deepEqual([i.into, i.need, i.pct], [75, 150, 50]);
  assert.equal(R.levelInfo(-5).level, 1);
  assert.equal(R.levelInfo(NaN).level, 1);
});
test("المضاعف: بلس والأدمن ×2 والمجاني ×1، وخطة مجهولة = مجاني", () => {
  assert.equal(R.multiplier("free"), 1);
  assert.equal(R.multiplier("plus_m"), 2);
  assert.equal(R.multiplier("plus_y"), 2);
  assert.equal(R.multiplier("admin"), 2);
  assert.equal(R.multiplier("xyz"), 1);
});
test("النقاط: مضاعف + سقف يومي 300، والأدمن بلا سقف", () => {
  assert.equal(R.awardAmount({ plan: "free", dayPlay: 0 }, 20), 20);
  assert.equal(R.awardAmount({ plan: "plus_m", dayPlay: 0 }, 20), 40);
  assert.equal(R.awardAmount({ plan: "free", dayPlay: 290 }, 20), 10);
  assert.equal(R.awardAmount({ plan: "free", dayPlay: 300 }, 20), 0);
  assert.equal(R.awardAmount({ plan: "plus_y", dayPlay: 280 }, 20), 20);
  assert.equal(R.awardAmount({ plan: "admin", dayPlay: 9999 }, 20), 40);
  assert.equal(R.awardAmount({ plan: "free", dayPlay: 0 }, -7), 0);
});
test("القفل: الأربع ألعاب لبلس والأدمن بس", () => {
  for (const g of ["auction", "wheel", "pictionary", "connect"]) {
    assert.equal(R.canPlay("free", g), false);
    assert.equal(R.canPlay("plus_m", g), true);
    assert.equal(R.canPlay("admin", g), true);
  }
  for (const g of ["hasm", "sahra", "points", "mafia", "speed"]) assert.equal(R.canPlay("free", g), true);
  assert.equal(R.tierOf("wheel"), "plus");
  assert.equal(R.tierOf("hasm"), null);
});
test("رقم هاتف أردني: صيغ مقبولة ومرفوضة", () => {
  for (const ok of ["0791234567", "791234567", "+962791234567", "00962791234567", "962 79 123 4567", "٠٧٩١٢٣٤٥٦٧", "078-123-4567", "077 1234567"])
    assert.equal(A.normalizePhone(ok), ok.includes("78") ? "+962781234567" : ok.includes("77") ? "+962771234567" : "+962791234567", ok);
  for (const bad of ["", "0791234", "0691234567", "07912345678", "abc", "+971501234567", "0701234567", null, undefined])
    assert.equal(A.normalizePhone(bad), null, String(bad));
});
test("الأدمن: بيانات الدخول والكود التجريبي", () => {
  assert.deepEqual(A.ADMIN_CREDENTIALS, { username: "admin", password: "admin" });
  assert.equal(A.TEST_SMS_CODE, "123456");
});
