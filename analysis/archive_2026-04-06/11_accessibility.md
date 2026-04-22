## Accessibility (Erişilebilirlik) Analiz Raporu
> Lead: ArtLead (A9) | Model: Sonnet 4.6

### Mevcut Durum

**Güçlü yanlar:**
- `<html lang="en">` tanımlanmış — temel dil bildirimi mevcut
- Form `<label>` elementleri input'larla ilişkilendirilmiş (`htmlFor` olmasa da wrapping label pattern)
- `autoFocus` AddProfileModal'da kullanılmış — modal açılınca odak otomatik gidiyor
- `type="password"` API Secret için doğru kullanılmış
- Semantic HTML kısmen var: `<header>`, `<main>`, `<table>`, `<thead>`, `<tbody>` SharePage'de
- `disabled` attribute form butonlarında doğru kullanılmış
- `placeholder` text bilgi taşıyor (ancak tek başına yeterli değil — aşağıya bak)

**Puan: 2.5/10**

---

### Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Modal'larda focus trap yok — açık modal'dan Tab ile dışarı çıkılabiliyor; screen reader kullanıcısı arkadaki içeriğe geçiyor | High | `focus-trap-react` veya custom hook ile modal açıkken Tab/Shift+Tab modal içinde döngüsel kalmalı | M |
| 2 | Modal'larda `role="dialog"`, `aria-modal="true"`, `aria-labelledby` yok — screen reader modal'ı anlayamıyor | High | Her modal div'ine `role="dialog" aria-modal="true" aria-labelledby="modal-title"` ekle | S |
| 3 | ESC ile modal kapatma desteği yok — klavye kullanıcıları modal'ı kapatmak için fare kullanmak zorunda | High | `useEffect` + `keydown` listener → ESC → `onClose()` | S |
| 4 | `<label>` htmlFor bağlantısı eksik — `htmlFor` attribute kullanılmamış, input'larla explicit ilişki kurulmamış; screen reader label'ı okuyamıyor | High | Her `<label>`'e `htmlFor="input-id"`, her `<input>`'a `id="input-id"` ekle | S |
| 5 | AllocationChart (PieChart) tamamen görsele dayalı — renk körü kullanıcılar için veri okunamaz; alternatif metin yok | High | `aria-label` veya hidden `<table>` olarak alternatif veri temsili; Recharts Pie'a `role="img" aria-label="Asset allocation chart"` | M |
| 6 | Button'larda icon olmasa da bazı butonlar bağlam olmadan anlaşılmıyor — `"Copy URL"`, `"Revoke"` hangi link için? | High | `aria-label="Copy URL for [link label]"` ve `aria-label="Revoke [link label] share link"` | S |
| 7 | Confirm dialog `window.confirm()` — screen reader'larda beklenmedik davranış, keyboard-only kullanıcı için erişilebilir değil | High | Custom modal ile destructive confirmation (bkz. #1 UI raporu) | M |

---

### İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Renk kontrast oranı — `text-gray-400` (#9ca3af) üzerine `bg-gray-900` (#111827) WCAG AA için 4.5:1 eşiğinde sorunlu olabilir; `text-gray-500` daha düşük kontrast | High | Contrast checker ile tüm text/background çiftlerini doğrula; gerekirse `text-gray-300` | M |
| 2 | Focus indicator görünmez — `focus:outline-none` tüm interactive elementlerde kullanılmış; klavye navigasyonunda odak hiç görünmüyor | High | `focus:outline-none`'ı kaldır, yerine `focus-visible:ring-2 focus-visible:ring-blue-500` ekle | S |
| 3 | Error mesajları `aria-live` bölgesinde değil — hata oluştuğunda screen reader otomatik okumaz | Med | Error container'a `role="alert"` veya `aria-live="polite"` ekle | S |
| 4 | Table'da `scope` attribute yok — SharePage'deki tablo header'larına `scope="col"` ekle | Med | `<th scope="col">` | S |
| 5 | Loading state screen reader'a bildirilmiyor | Med | Loading div'ine `role="status" aria-live="polite" aria-label="Portfolio yükleniyor"` | S |
| 6 | ProfileSwitcher butonları `aria-pressed` ile state bildirmiyor | Low | Aktif profil butonu için `aria-pressed="true"` | S |
| 7 | `<h1>` hiyerarşisi tutarsız — Dashboard'da "CoinHQ" h1, Settings'de "Settings" h1; ancak SharePage'de `<header>` içinde h1 yok | Low | Her sayfada tek h1, doğru heading hiyerarşisi (h1 → h2 → h3) | S |

---

### Kesin Olmalı (industry standard)

- **WCAG 2.1 AA kontrast oranı:** Normal metin 4.5:1, büyük metin 3:1 — özellikle `text-gray-400`, `text-gray-500` review gerek
- **Klavye navigasyonu:** Tab sırası mantıklı, focus ring görünür, modal trap çalışıyor
- **Screen reader anlaşılırlığı:** Tüm interactive elementlerde anlamlı label (text veya aria-label)
- **Semantic HTML:** `<main>`, `<nav>`, `<header>`, `<section>`, `<article>` doğru yerlerde kullanılmalı — şu an dashboard ve settings tamamen `<div>` tabanlı
- **Form erişilebilirliği:** label-input ilişkisi, required alanlar `aria-required="true"`, hata mesajları `aria-describedby` ile input'a bağlı

---

### Kesin Değişmeli (mevcut sorunlar)

- `focus:outline-none` → `focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900`
- Tüm modal div'lerine `role="dialog" aria-modal="true"` + ESC support
- `<label>` → `htmlFor` + `<input>` → `id` explicit bağlantı
- Tüm `window.confirm()` kaldır → custom modal
- AllocationChart'a `role="img"` + `aria-label` + hidden data table alternatifi

---

### Nice-to-Have (diferansiasyon)

- `prefers-reduced-motion` media query — animasyon/transition'ları indirgeme
- `prefers-color-scheme` desteği — dark/light sistem tercihine göre otomatik
- Skip navigation link (`<a href="#main-content" className="sr-only focus:not-sr-only">Skip to main content</a>`)
- Exchange balance sayısı için `aria-live="polite"` güncelleme bildirimi
- ARIA landmark'lar: `role="navigation"`, `role="main"`, `role="complementary"`
- axe-core veya jest-axe ile otomatik a11y test pipeline

---

### Test Önerisi

Kısa vadede şu araçlarla hızlı kontrol yapılabilir:
1. Chrome DevTools → Lighthouse → Accessibility audit
2. `Tab` tuşuyla tüm sayfada klavye gezintisi — odak görünmezse kritik sorun
3. macOS VoiceOver (`Cmd+F5`) ile modal açıp okuma testi
