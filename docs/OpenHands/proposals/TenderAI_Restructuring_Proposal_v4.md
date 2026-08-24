
# TenderAI — Restructuring Proposal (v4-development)

> Generated: 2026-08-24 · Branch: v4-development  
> Scope: Folder restructure + route fixes + React-vs-Streamlit evaluation

---

## 1. Current State (from full codebase scan)

- Pages: 14 public files (`landing_page*`, `about.py`, `blog.py`, `faq.py`, `login.py`, `register.py`, `pricing_page.py`, `contact.py`) + 6 app files (`dashboard.py`, `company_dashboard.py`, `admin_dashboard*`, `tender_analysis.py`, `profile.py`) — all flat in `_pages/`.
- Main app (`main.py`): ~88KB, 81 imports, 11 page-handler references, embedded CSS (`!important` overrides), role-based sidebar (`render_sidebar()` at line 842).
- UI modules (`modules/`): 20+ files mixing auth/access/business logic; no `frontend/` layer.
- API (`api/`): `flask_api.py`, `extension_api.py`, `tenant_rate_api.py` — clean boundary.
- Mobile/Responsive: No `@media` breakpoints; fixed `0.95rem` font; sidebar always expanded.
- Duplicates: 4 landing pages (`landing_page`, `landing_page2`, `landing_page3`, `landing_page_4` / `landing_page2 copy.py`).
- Routes: `main.py` maps strings (`'home'`, `'pricing'`, `'contact'`) to functions; moving files requires updating these mappings and any `st.switch_page()` links.

---

## 2. Option A — Streamlit Restructure (Recommended First Step)

Folders: `public/`, `app/`, `frontend/styles/`, `frontend/components/`, `backend/services/`.
Route updates: `main.py` imports + sidebar links + Streamlit multi-page URL paths (`/public/landing`).
Effort: Low (1–2 days). Keeps existing deploy (Streamlit Cloud / Docker).

---

## 3. Option B — React + JSON Migration

Path: Separate `frontend/` (React/Vite) consuming `api/` JSON; keep `backend/` Python.
Phase 1: Do Option A (folder split) to stabilize API contracts.  
Phase 2: Build React frontend; deprecate `main.py`.  
Effort: 3–4 weeks. Requires JS/React skills; solves mobile/responsive gaps fully.

---

## 4. Recommendation

**Do Option A now.** It fixes folder separation, eliminates landing duplicates, extracts CSS to `frontend/`, and updates routes. It prepares the codebase for Option B without committing to a full framework migration.

---

## 5. Immediate Actions (If You Proceed)

1. `git mv` public/app files.
2. Consolidate landing duplicates.
3. Update `main.py` page handlers and sidebar.
4. Create `frontend/styles/global.css` + `frontend/config/theme.py`.
5. Add mobile `@media` rules.
6. Update `.streamlit/config.toml` if needed.
