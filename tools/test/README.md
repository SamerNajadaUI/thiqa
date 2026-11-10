# فحص الألعاب

```bash
cd tools/test && npm install                 # مرة وحدة (aedes + mqtt)
(cd ../../docs && python3 -m http.server 8765 &)
node broker.js &                             # سيرفر MQTT محلي على ws://localhost:8883
node sahra_local.js full ball                # سهرة كاملة على تلفون واحد (full|quick, mix|ball)
node sahra_online.js                         # غرفة من 4 تلفونات + ريفرش بالنص
```

الصور بتنحفظ بـ`shots/` (مش بالريبو). `?fast` بالرابط بيقصّر وقت التمثيل والقنبلة للفحص بس.
