# خطة تنفيذ هيكل التطبيق

الوثيقة: `specs/2026-11-10-app-shell-design.md`. التنفيذ بنفس الجلسة (native) بطلب سامر «كمّل بدون ما تسألني».

## قرارات اتخذتها بدل ما أسأل (سامر قال لا تسألني)
- **الأسعار (تجريبية):** بلس شهري 2.99 د.أ، بلس سنوي 24.99 د.أ.
- **اللي بينقفل على بلس:** المزاد، عجلة الحظ، ارسم وخمّن، إكس أو بالجاذبية. الألعاب الكبيرة بتضل مجانية.
- **بلس:** نقاط ×2، الألعاب الأربعة، وشارة. الأدمن: ×2 وبدون سقف يومي وكل شي مفتوح.
- **كود SMS التجريبي (وضع محلي):** `123456`، ومكتوب بالشاشة إنه تجريبي.
- **وحدة واحدة `app/core.js`** بدل ملفات منفصلة، عشان تنحمّل بسطر واحد وبشكل متزامن بكل صفحة قبل الحارس. المنطق الصافي (مستوى، مضاعف، سقف، رقم هاتف) بيصدّر لـNode للفحص.
- جوجل وأبل بالوضع المحلي: حساب تجريبي على الجهاز. بالوضع الحقيقي (لما `firebase-config.js` ينعبّى) بيشتغلوا بـFirebase. كود Firebase مكتوب وما أقدر أفحصه بدون مفاتيح.

## المهام
1. **سيستم التصميم:** `docs/ds/ds.css` (tokens البراند، مكوّنات، جرادينت)؛ `shell.css` بيستورد ds.css وبتتغيّر ألوان `.g-<id>`؛ `theme.js` (theme-color)؛ أيقونة التطبيق بألوان البراند.
2. **المنطق:** `docs/app/core.js` (AppStore، Auth محلي، Rewards، Gate) + `auth-firebase.js` + `firebase-config.js`. فحص: `tools/test/app_core.test.js`.
3. **الصفحات:** `index.html` سبلاش وموجّه، `login.html`، `home.html` (الرئيسية القديمة منقولة ومعدّلة)، تعديل `games/index.html` (شرائح وترتيب)، `rewards.html`، `settings.html`، `ds/index.html`، و`app/ui.js` (شريط التبويب).
4. **الربط:** سطر `core.js` بكل صفحات الألعاب (حارس + قفل + نقاط الوقت)، `Rewards.finish` بنهاية ملك السهرة وليلة الحسم، `sw.js` v14.
5. **الفحص:** Node للمنطق، Playwright بـ390px لكل التدفق بالفاتح والغامق، سكربت الألوان والتباين، وتشغيل «ليلة الحسم» آلياً.

## واجهات
```
Auth.user() Auth.onChange(cb) Auth.signOut() Auth.update(patch)
Auth.signInGoogle() Auth.signInApple() Auth.sendPhoneCode(raw) Auth.confirmPhoneCode(code) Auth.signInAdmin(u,p)
Auth.normalizePhone(raw) -> "+9627XXXXXXXX" | null
Rewards.levelInfo(points) -> {level,name,into,need,pct}
Rewards.multiplier(plan) Rewards.canPlay(plan, gameId) Rewards.dailyRemaining(user)
Rewards.add(base, reason) Rewards.finish(gameId, base=20) Rewards.setPlan(plan)
```
