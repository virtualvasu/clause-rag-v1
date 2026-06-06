---
name: Emerald Legal
colors:
  surface: '#0c1324'
  surface-dim: '#0c1324'
  surface-bright: '#33394c'
  surface-container-lowest: '#070d1f'
  surface-container-low: '#151b2d'
  surface-container: '#191f31'
  surface-container-high: '#23293c'
  surface-container-highest: '#2e3447'
  on-surface: '#dce1fb'
  on-surface-variant: '#bfc9c3'
  inverse-surface: '#dce1fb'
  inverse-on-surface: '#2a3043'
  outline: '#89938d'
  outline-variant: '#404944'
  surface-tint: '#95d3ba'
  primary: '#95d3ba'
  on-primary: '#003829'
  primary-container: '#064e3b'
  on-primary-container: '#80bea6'
  inverse-primary: '#2b6954'
  secondary: '#ffb68e'
  on-secondary: '#532200'
  secondary-container: '#ab4c00'
  on-secondary-container: '#ffe2d5'
  tertiary: '#c4c7c9'
  on-tertiary: '#2d3133'
  tertiary-container: '#424547'
  on-tertiary-container: '#afb2b4'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b0f0d6'
  primary-fixed-dim: '#95d3ba'
  on-primary-fixed: '#002117'
  on-primary-fixed-variant: '#0b513d'
  secondary-fixed: '#ffdbca'
  secondary-fixed-dim: '#ffb68e'
  on-secondary-fixed: '#331200'
  on-secondary-fixed-variant: '#763300'
  tertiary-fixed: '#e0e3e5'
  tertiary-fixed-dim: '#c4c7c9'
  on-tertiary-fixed: '#191c1e'
  on-tertiary-fixed-variant: '#444749'
  background: '#0c1324'
  on-background: '#dce1fb'
  surface-variant: '#2e3447'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0em
  body-lg:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: 0em
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: 0em
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: 0.01em
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Geist
    fontSize: 10px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.08em
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style
The brand personality is authoritative, architectural, and unwavering. This design system moves away from generic software aesthetics toward a high-end, institutional feel reminiscent of prestigious law firms and modern architectural bureaus. The target audience consists of legal professionals, corporate executives, and high-stakes stakeholders who value precision and discretion.

The design style is **Modernist Minimalism with a Structured Edge**. It prioritizes extreme clarity, crisp lines, and an intentional lack of decorative fluff. The UI evokes a sense of permanence and reliability through deep, saturated backgrounds and high-contrast typographic hierarchies. Expect a dense, information-rich environment that remains legible and organized through strict alignment and structural integrity.

## Colors
The palette is built on a foundation of "Deep Forest Black" to provide a sophisticated, low-glare workspace for long-form document review. 

- **Primary (Emerald):** Used for key actions and brand presence. It should feel deep and saturated, not neon.
- **Secondary (Brass/Gold):** Reserved for highlights, critical status indicators, or refined accents that break the monochromatic baseline.
- **Surface & Surface-Bright:** Used to create structural hierarchy. The darker `#020617` is the primary canvas, while `#0f172a` is used for headers, sidebars, and active containers.
- **Contrast:** Typography and icons utilize high-value off-whites (`#f8fafc`) to ensure maximum legibility against the dark background without the harshness of pure white.

## Typography
This design system utilizes **Geist** for its technical precision and monospaced-influenced tracking, which fits the legal/contractual context perfectly. 

The type scale is modular and emphasizes a strong vertical rhythm. Headlines use tight letter spacing and a heavy weight to appear grounded. Body text is optimized for long-form reading with generous line heights. Labels are exclusively uppercase with increased letter-spacing to act as architectural "markers" within the UI. All text should be rendered with `antialiased` smoothing.

## Layout & Spacing
The layout follows a **Strict Fixed Grid** philosophy. On desktop, content is centered within a 1440px container using a 12-column system. 

Spacing is based on a 4px baseline grid. Internal component spacing (padding/gap) should strictly adhere to these increments to maintain a sense of mathematical order. 
- **Desktop:** 24px gutters, 48px outer margins.
- **Tablet:** 16px gutters, 32px outer margins.
- **Mobile:** 16px gutters, 16px outer margins.

The design system avoids fluid "squishiness." Elements should snap to grid lines, and vertical spacing between sections should be aggressive (`xl`) to create distinct "rooms" for different information sets.

## Elevation & Depth
Elevation is achieved through **Tonal Layering and Sharp Outlines**, rather than shadows. 

The design system is intentionally flat to emphasize its modernist roots. Instead of depth via light-sources, we use:
1.  **Z-Index Tiering:** Lower tiers use the darkest Neutral color. Higher tiers (modals, popovers) use Surface-Bright.
2.  **Ghost Borders:** Every container must have a 1px solid border. Use `#1e293b` (a slightly lighter slate) for standard containers and the Primary Emerald or Secondary Brass for active/focused states.
3.  **Strict Zero-Shadow:** No drop shadows are permitted. If a floating element needs to be distinguished, increase the contrast of its border or add a 2px offset "solid shadow" using a solid color block behind the element.

## Shapes
The shape language is **Strictly Square (Sharp)**. 

Every UI element—including buttons, input fields, cards, and tags—must have a 0px border radius. This reinforces the architectural and institutional feel of the brand. Circular shapes are only permitted for user avatars or specific status dots to ensure they stand out as "organic" elements within a "structured" environment.

## Components

- **Buttons:** Primary buttons use a solid Emerald background with White text. Secondary buttons use a 1px Brass border with Brass text. All buttons have a hover state that shifts the background color by 10% (darker) or adds a solid 2px offset border.
- **Input Fields:** 1px solid border (`#1e293b`), background is the base neutral. Focus state switches the border to Brass. Labels sit strictly above the input in the `label-md` style.
- **Cards:** No shadows. 1px solid border. Headers within cards should have a 1px bottom border to separate them from the body content.
- **Lists/Data Tables:** Use thin 1px horizontal dividers only. Row hover states should use a subtle highlight of Surface-Bright (`#0f172a`).
- **Chips/Status:** Rectangular with a 1px border. Status colors should be muted but distinct (e.g., a dark red for "Flagged," the primary emerald for "Executed").
- **Legal Markers:** A custom component for document view—a vertical bar on the left side of a paragraph using the Secondary Brass color to indicate "Highlighted" or "Clause of Interest."