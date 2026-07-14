// Theme system - Dark, Light, Custom themes
const ThemeManager = {
    current: 'dark',
    themes: {
        dark: {
            name: 'Dark',
            bg: { primary: '#0f172a', secondary: '#1e293b', tertiary: '#334155' },
            text: { primary: '#f1f5f9', secondary: '#cbd5e1', muted: '#94a3b8' },
            border: '#475569',
            accent: '#6366f1',
            success: '#10b981', warning: '#f59e0b', danger: '#ef4444', info: '#3b82f6',
            gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)',
        },
        light: {
            name: 'Light',
            bg: { primary: '#ffffff', secondary: '#f8fafc', tertiary: '#e2e8f0' },
            text: { primary: '#0f172a', secondary: '#475569', muted: '#64748b' },
            border: '#cbd5e1',
            accent: '#6366f1',
            success: '#059669', warning: '#d97706', danger: '#dc2626', info: '#2563eb',
            gradient: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
        },
        cyberpunk: {
            name: 'Cyberpunk',
            bg: { primary: '#0a0e27', secondary: '#1a1f3a', tertiary: '#2a2f4a' },
            text: { primary: '#00ff9f', secondary: '#ff00ff', muted: '#00d9ff' },
            border: '#ff00ff',
            accent: '#00ff9f',
            success: '#00ff9f', warning: '#ffea00', danger: '#ff0055', info: '#00d9ff',
            gradient: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #2a2f4a 100%)',
        },
        ocean: {
            name: 'Ocean',
            bg: { primary: '#001f3f', secondary: '#003366', tertiary: '#004080' },
            text: { primary: '#e0f2ff', secondary: '#b3d9ff', muted: '#80bfff' },
            border: '#0077b6',
            accent: '#00b4d8',
            success: '#06d6a0', warning: '#ffd60a', danger: '#ef476f', info: '#118ab2',
            gradient: 'linear-gradient(135deg, #001f3f 0%, #003366 50%, #004080 100%)',
        },
        forest: {
            name: 'Forest',
            bg: { primary: '#0d1b0d', secondary: '#1b3a1b', tertiary: '#2d4a2d' },
            text: { primary: '#d4f4dd', secondary: '#a8d5ba', muted: '#7cb694' },
            border: '#3a6b3a',
            accent: '#52b788',
            success: '#95d5b2', warning: '#ffd166', danger: '#e63946', info: '#a8dadc',
            gradient: 'linear-gradient(135deg, #0d1b0d 0%, #1b3a1b 50%, #2d4a2d 100%)',
        },
        midnight: {
            name: 'Midnight',
            bg: { primary: '#000000', secondary: '#0a0a0a', tertiary: '#1a1a1a' },
            text: { primary: '#ffffff', secondary: '#cccccc', muted: '#999999' },
            border: '#333333',
            accent: '#bb86fc',
            success: '#03dac6', warning: '#cf6679', danger: '#cf6679', info: '#bb86fc',
            gradient: 'linear-gradient(135deg, #000000 0%, #0a0a0a 50%, #1a1a1a 100%)',
        },
        dracula: {
            name: 'Dracula',
            bg: { primary: '#282a36', secondary: '#44475a', tertiary: '#6272a4' },
            text: { primary: '#f8f8f2', secondary: '#bd93f9', muted: '#6272a4' },
            border: '#44475a',
            accent: '#bd93f9',
            success: '#50fa7b', warning: '#f1fa8c', danger: '#ff5555', info: '#8be9fd',
            gradient: 'linear-gradient(135deg, #282a36 0%, #44475a 50%, #6272a4 100%)',
        },
        nord: {
            name: 'Nord',
            bg: { primary: '#2e3440', secondary: '#3b4252', tertiary: '#434c5e' },
            text: { primary: '#eceff4', secondary: '#e5e9f0', muted: '#d8dee9' },
            border: '#4c566a',
            accent: '#88c0d0',
            success: '#a3be8c', warning: '#ebcb8b', danger: '#bf616a', info: '#5e81ac',
            gradient: 'linear-gradient(135deg, #2e3440 0%, #3b4252 50%, #434c5e 100%)',
        },
    },
    custom: null,

    init() {
        const saved = localStorage.getItem('recon_theme');
        if (saved) this.applyTheme(saved);
        else this.applyTheme('dark');
    },

    applyTheme(themeName) {
        let theme = themeName === 'custom' ? this.custom : this.themes[themeName];
        if (!theme) return;
        this.current = themeName;
        const root = document.documentElement;
        root.style.setProperty('--bg-primary', theme.bg.primary);
        root.style.setProperty('--bg-secondary', theme.bg.secondary);
        root.style.setProperty('--bg-tertiary', theme.bg.tertiary);
        root.style.setProperty('--text-primary', theme.text.primary);
        root.style.setProperty('--text-secondary', theme.text.secondary);
        root.style.setProperty('--text-muted', theme.text.muted);
        root.style.setProperty('--border-color', theme.border);
        root.style.setProperty('--accent-color', theme.accent);
        root.style.setProperty('--success-color', theme.success);
        root.style.setProperty('--warning-color', theme.warning);
        root.style.setProperty('--danger-color', theme.danger);
        root.style.setProperty('--info-color', theme.info);
        document.body.style.background = theme.gradient;
        localStorage.setItem('recon_theme', themeName);
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: themeName, colors: theme } }));
    },

    createCustom(config) {
        this.custom = { name: 'Custom', ...config };
        this.applyTheme('custom');
    },

    cycleTheme() {
        const names = Object.keys(this.themes);
        const idx = names.indexOf(this.current);
        const next = names[(idx + 1) % names.length];
        this.applyTheme(next);
    },

    getAvailableThemes() {
        return Object.keys(this.themes).map(k => ({ id: k, name: this.themes[k].name }));
    },
};

if (typeof window !== 'undefined') {
    window.ThemeManager = ThemeManager;
    document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
}
