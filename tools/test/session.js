// يدخّل حساب أدمن محلي قبل ما تنفتح أي صفحة، عشان حارس الدخول ما يحوّل فحوصات الألعاب لصفحة الدخول.
exports.adminInit = () => {
  try {
    localStorage.setItem('app-users', JSON.stringify({ admin: { uid: 'admin', name: 'الأدمن', provider: 'admin', plan: 'admin', points: 0, dayKey: '', dayPlay: 0, lastDaily: '' } }));
    localStorage.setItem('app-session', '"admin"');
  } catch {}
};
