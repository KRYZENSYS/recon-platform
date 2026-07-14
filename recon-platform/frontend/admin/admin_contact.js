// Admin Contact Functions - Reusable
const AdminContact = {
  info: {
    name: "Firdavs (FirdavsVIP)",
    role: "Founder & Lead Developer",
    organization: "KRYZENSYS",
    email: "f91186645@gmail.com",
    telegram: {
      username: "FirdavsVIP",
      url: "https://t.me/FirdavsVIP",
      display: "@FirdavsVIP"
    },
    github: {
      username: "KRYZENSYS",
      url: "https://github.com/KRYZENSYS/",
      display: "github.com/KRYZENSYS"
    }
  },

  async load() {
    try {
      const res = await fetch('/api/v1/admin/contact');
      if (res.ok) {
        const data = await res.json();
        this.info = { ...this.info, ...data.admin };
      }
    } catch (e) {
      console.log('Using default admin contact');
    }
  },

  render() {
    const i = this.info;
    return `
      <div class="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6 mt-6">
        <h3 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
          <span>📞</span> Admin Contact
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a href="mailto:${i.email}" class="group bg-white/5 hover:bg-white/10 border border-white/10 hover:border-indigo-500/50 rounded-xl p-5 transition-all duration-300 hover:scale-105">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-10 h-10 bg-indigo-500/20 rounded-lg flex items-center justify-center text-xl">📧</div>
              <span class="text-xs uppercase tracking-wider text-slate-400">Email</span>
            </div>
            <div class="text-white font-semibold break-all">${i.email}</div>
            <div class="text-xs text-slate-400 mt-1">Bosing - email ochish uchun</div>
          </a>
          <a href="${i.github.url}" target="_blank" rel="noopener" class="group bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/50 rounded-xl p-5 transition-all duration-300 hover:scale-105">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center text-xl">💻</div>
              <span class="text-xs uppercase tracking-wider text-slate-400">GitHub</span>
            </div>
            <div class="text-white font-semibold break-all">${i.github.display}</div>
            <div class="text-xs text-slate-400 mt-1">Yangi tab'da ochish ↗</div>
          </a>
          <a href="${i.telegram.url}" target="_blank" rel="noopener" class="group bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-500/50 rounded-xl p-5 transition-all duration-300 hover:scale-105">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center text-xl">📱</div>
              <span class="text-xs uppercase tracking-wider text-slate-400">Telegram</span>
            </div>
            <div class="text-white font-semibold">${i.telegram.display}</div>
            <div class="text-xs text-slate-400 mt-1">Telegram'da yozish ✈️</div>
          </a>
        </div>
        <div class="mt-6 pt-6 border-t border-white/10">
          <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div class="text-white font-semibold flex items-center gap-2">
                👤 ${i.name}
                <span class="text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded-full">${i.role}</span>
              </div>
              <div class="text-sm text-slate-400 mt-1">${i.organization} · Professional Security Solutions</div>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-400">
              <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              <span>Online · 24 soat ichida javob</span>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  async inject(containerId) {
    await this.load();
    const container = document.getElementById(containerId);
    if (container) container.innerHTML = this.render();
  },

  sendEmail(subject = '', body = '') {
    const mailto = `mailto:${this.info.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
  },

  openTelegram() {
    window.open(this.info.telegram.url, '_blank');
  },

  openGitHub() {
    window.open(this.info.github.url, '_blank');
  }
};

if (typeof window !== 'undefined') {
  window.AdminContact = AdminContact;
  document.addEventListener('DOMContentLoaded', () => AdminContact.inject('admin-contact-container'));
}
