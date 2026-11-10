// مزوّد Firebase الحقيقي (جوجل، أبل، رقم أردني) + حفظ مستند اللاعب بـFirestore.
// ما انفحص مقابل مشروع حقيقي (ما في مفاتيح)، لذلك أول تشغيل بحاجة تجربة.
// بيتحمّل بس لما window.APP_FIREBASE_CONFIG ينعبّى.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import { getAuth, GoogleAuthProvider, OAuthProvider, signInWithPopup, RecaptchaVerifier, signInWithPhoneNumber, signOut } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";
import { getFirestore, doc, getDoc, setDoc } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";

const app = initializeApp(window.APP_FIREBASE_CONFIG);
const auth = getAuth(app);
auth.languageCode = "ar";
const db = getFirestore(app);
let confirmation = null, verifier = null;

// المستند عند السيرفر هو المرجع للنقاط والخطة، وبندمجه فوق النسخة المحلية
async function hydrate(fbUser, provider, extra, users, saveUser, blank) {
  const uid = fbUser.uid;
  const local = users()[uid] || blank(uid, { name: fbUser.displayName || extra.name || "لاعب", provider, email: fbUser.email || null, phone: fbUser.phoneNumber || null });
  try { const snap = await getDoc(doc(db, "users", uid)); if (snap.exists()) Object.assign(local, snap.data()); } catch (e) { console.warn("firestore read", e); }
  saveUser(local);
  setDoc(doc(db, "users", uid), local, { merge: true }).catch(() => {});
  return local;
}

window.__fbResolve({
  async social(kind, users, saveUser, blank) {
    const provider = kind === "google" ? new GoogleAuthProvider() : new OAuthProvider("apple.com");
    if (kind === "apple") { provider.addScope("name"); provider.addScope("email"); }
    const res = await signInWithPopup(auth, provider);
    return hydrate(res.user, kind, {}, users, saveUser, blank);
  },
  async sendCode(phone) {
    if (!verifier) {
      let el = document.getElementById("recaptcha"); if (!el) { el = document.createElement("div"); el.id = "recaptcha"; document.body.appendChild(el); }
      verifier = new RecaptchaVerifier(auth, el, { size: "invisible" });
    }
    confirmation = await signInWithPhoneNumber(auth, phone, verifier);
  },
  async confirm(code, users, saveUser, blank) {
    if (!confirmation) throw new Error("ابعت الكود أول");
    const res = await confirmation.confirm(code);
    return hydrate(res.user, "phone", {}, users, saveUser, blank);
  },
  push(u) { if (!auth.currentUser || auth.currentUser.uid !== u.uid) return; setDoc(doc(db, "users", u.uid), u, { merge: true }).catch(() => {}); },
  signOut() { return signOut(auth).catch(() => {}); },
});
