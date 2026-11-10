# فحص الألعاب

```bash
cd tools/test && npm install                 # مرة وحدة (aedes + mqtt)
(cd ../../docs && python3 -m http.server 8765 &)
node broker.js &                             # سيرفر MQTT محلي على ws://localhost:8883
node sahra_local.js full ball                # سهرة كاملة على تلفون واحد (full|quick, mix|ball)
node sahra_online.js                         # غرفة من 4 تلفونات + ريفرش بالنص

# ليلة الحسم
node --test hasm_core.test.js                # القواعد: جدول، مزاد، كروت، ألغاز، و300 موسم بالكمبيوتر
node hasm_local.js 3 quick                   # موسم على تلفون واحد (عدد اللاعبين 1-6، quick|full، و slow لصور الأنيميشن)
node hasm_online.js                          # غرفة 3 تلفونات + كمبيوتر، ريفرش، ضيف ما بيختار، وفحص تسريب الأسرار
```

الصور بتنحفظ بـ`shots/` (مش بالريبو). `?fast` بالرابط بيقصّر وقت التمثيل والقنبلة للفحص بس.

# التطبيق (حسابات ونقاط وخطط)
```bash
node --test app_core.test.js     # منطق: مستوى، مضاعف، سقف يومي، قفل، رقم أردني
node app_flow.js                 # التدفق كامل بـ390px، وصور بـshots/app-*.png
node app_games_smoke.js          # كل صفحات الألعاب بدون أخطاء JS
node ds_check.js                 # ألوان خارج البراند + تباين WCAG
```
سكربتات الألعاب بتدخل بحساب أدمن محلي عبر `session.js` (الحارس بيحوّل أي صفحة لعبة للدخول بدونه).
