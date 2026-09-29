/**
 * BHUMISETU 2026 DESIGN SYSTEM TOKENS
 * 
 * Digital Public Infrastructure (DPI) & Enterprise Land Intelligence Standard
 * Principles: Content > Decoration | Data > Marketing | Tasks > Banners
 * Accessibility: WCAG 2.1 AA / GIGW 3.0 Compliant
 */

export const tokens = {
  colors: {
    // Government Authority & Sovereign Foundation
    brand: {
      navyDark: '#0A2540',
      navyPrimary: '#0B3866',
      navyMedium: '#134679',
      navyLight: '#205C99',
      navySubtle: '#F0F6FB',
    },
    // Sovereign Accent (Restrained Saffron)
    accent: {
      saffron: '#F37021',
      saffronDark: '#D95A10',
      saffronSubtle: '#FFF7ED',
      saffronBorder: '#FED7AA',
    },
    // Neutral Canvas & Elevation Surfaces
    neutral: {
      canvas: '#F8FAFC',
      surface: '#FFFFFF',
      surfaceSubtle: '#F1F5F9',
      surfaceHover: '#F8FAFC',
      card: '#FFFFFF',
    },
    // Typography Hierarchy
    text: {
      heading: '#0F172A',
      body: '#1E293B',
      muted: '#475569',
      subdued: '#64748B',
      inverse: '#FFFFFF',
      inverseMuted: '#94A3B8',
    },
    // Borders
    border: {
      subtle: '#E2E8F0',
      default: '#CBD5E1',
      strong: '#94A3B8',
      focus: '#0B3866',
    },
    // Semantic States (Restrained, Non-Screaming)
    semantic: {
      success: {
        text: '#166534',
        bg: '#F0FDF4',
        border: '#BBF7D0',
        icon: '#16A34A',
        badge: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      },
      warning: {
        text: '#9A3412',
        bg: '#FFFBEB',
        border: '#FDE68A',
        icon: '#D97706',
        badge: 'bg-amber-50 text-amber-800 border-amber-200',
      },
      danger: {
        text: '#991B1B',
        bg: '#FEF2F2',
        border: '#FECACA',
        icon: '#DC2626',
        badge: 'bg-red-50 text-red-800 border-red-200',
      },
      info: {
        text: '#1E40AF',
        bg: '#EFF6FF',
        border: '#BFDBFE',
        icon: '#2563EB',
        badge: 'bg-blue-50 text-blue-800 border-blue-200',
      },
      neutral: {
        text: '#334155',
        bg: '#F8FAFC',
        border: '#E2E8F0',
        icon: '#64748B',
        badge: 'bg-slate-50 text-slate-700 border-slate-200',
      }
    }
  },

  typography: {
    fontSans: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans Devanagari', sans-serif",
    fontMono: "'JetBrains Mono', 'SF Mono', Consolas, Menlo, monospace",
    sizes: {
      display: 'text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight',
      pageTitle: 'text-xl sm:text-2xl font-bold tracking-tight text-slate-900',
      sectionTitle: 'text-base sm:text-lg font-bold text-slate-900 tracking-tight',
      cardTitle: 'text-sm sm:text-base font-semibold text-slate-800',
      body: 'text-xs sm:text-sm text-slate-700 leading-relaxed',
      caption: 'text-[11px] text-slate-500 font-medium leading-normal',
      micro: 'text-[10px] text-slate-400 font-semibold uppercase tracking-wider',
    }
  },

  radius: {
    sm: 'rounded-md',     // 6px - buttons, inputs
    default: 'rounded-lg', // 8px - table cells, inner cards
    md: 'rounded-xl',     // 12px - cards, panels
    lg: 'rounded-2xl',    // 16px - dialogs, main containers
    full: 'rounded-full', // pills - badges only
  },

  shadows: {
    subtle: 'shadow-xs',
    card: 'shadow-[0_1px_3px_0_rgba(15,23,42,0.04)]',
    cardHover: 'hover:shadow-[0_4px_12px_0_rgba(15,23,42,0.06)]',
    elevated: 'shadow-md',
    dropdown: 'shadow-lg border border-slate-200',
    modal: 'shadow-2xl border border-slate-200/90',
  }
} as const;

export type DesignTokens = typeof tokens;
