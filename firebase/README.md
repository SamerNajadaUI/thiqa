# ربط Firebase (حسابات حقيقية)

1. console.firebase.google.com ← Add project (مثلاً `abu-odeh`). Analytics مش ضروري.
2. **Authentication ← Sign-in method**: فعّل **Google** و**Phone** (و**Apple** لما يكون عندك Apple Developer).
3. **Authentication ← Settings ← Authorized domains**: أضف `samernajadaui.github.io`.
4. **Firestore Database ← Create database** (production mode)، وبعدين تبويب Rules والصق `firebase/firestore.rules` واعمل Publish.
5. **Project settings ← General ← Your apps ← Web (</>)**: سجّل تطبيق ويب وانسخ كائن `firebaseConfig`.
6. الصق القيم بـ`docs/app/firebase-config.js` مكان `null`:
   `window.APP_FIREBASE_CONFIG = { apiKey: "...", authDomain: "...", projectId: "...", appId: "..." };`
   (مفاتيح الويب عامة بطبيعتها، الحماية بالقواعد وبالدومينات المسموحة.)
7. الأرقام التجريبية للفحص: Authentication ← Phone ← Phone numbers for testing.

ملاحظات: SMS بعد الحد المجاني بيكلّف. جوجل ما بيشتغل داخل تطبيق الآيفون (WKWebView). أبل بدها Apple Developer مدفوع وService ID.
القواعد بتحمي مستند كل لاعب من غيره، بس الخطة والنقاط بيكتبها العميل لحد ما يكون في دفع/سيرفر، فهي مش مضادة للغش.
