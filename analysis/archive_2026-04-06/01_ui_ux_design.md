## UI/UX & Design Analiz Raporu
> Lead: ArtLead (A9) | Model: Sonnet 4.6

### Mevcut Durum

**Güçlü yanlar:**
- Dark mode-first yaklaşım tutarlı biçimde uygulanmış (`bg-gray-950`, `bg-gray-900`, `border-gray-800` hiyerarşisi)
- Tailwind CSS kullanımı standart ve tutarlı — spacing, border-radius, font-weight düzgün
- `rounded-xl` / `rounded-2xl` kartlar ve `border border-gray-800` çerçeveler görsel hiyerarşiyi kuruyor
- ProfileSwitcher'da pill-button pattern aktif/pasif state için `bg-blue-600` vs `bg-gray-800` ile net
- AllocationChart'ta Recharts ile çalışan pie chart var, dark tooltip özelleştirilmiş
- SharePage'de "Read-only portfolio view" badge'i UX açısından doğru bağlam kurmuş
- Inter font seçimi okunabilirlik için uygun
- Share sayfasında tablo layout'u verinin yapısına uygun
- Responsive grid: `grid-cols-1 lg:grid-cols-2` var

**Puan: 4.5/10**

---

### Kritik Eksikler (hemen yapılmalı)

| # | Sorun | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Login sayfası yok — `/dashboard`'a redirect direkt yapılıyor, unauthenticated kullanıcı için UI tasarımı eksik | High | `/login` sayfası oluştur; Google OAuth butonu, CoinHQ logo ve kısa tagline ile | M |
| 2 | Loading state primitif — "Loading portfolio..." plain text; spinner veya skeleton yok | High | Skeleton card component ekle (PortfolioSummary, ExchangeList için) | S |
| 3 | Design token sistemi yok — Tailwind `theme.extend` tamamen boş; renk/spacing sözlüğü raw class'larla inline yazılmış | High | `tailwind.config.ts`'de custom color palette tanımla: `brand`, `surface`, `border` token'ları | M |
| 4 | Navigation component yok — dashboard/settings arası sadece `<Link>` metni; aktif sayfa belli değil | High | Minimal sidebar veya top navbar ekle; aktif route için highlight | M |
| 5 | `confirm()` ile native browser dialog kullanılıyor (delete profile, delete key, revoke link) — modern UX değil | Med | Custom confirmation modal component yaz | S |

---

### İyileştirme Önerileri (planlı)

| # | Öneri | Etki | Çözüm | Efor |
|---|-------|------|-------|------|
| 1 | Dashboard'da "cached" indicator gösterilmiyor — API'den `cached: boolean` geliyor ama UI'da hiç kullanılmıyor | Med | PortfolioSummary'ye "Cached · 60s ago" badge ekle | S |
| 2 | ExchangeList'te top 5 asset limiti hardcode — kullanıcı tüm asset'leri göremez | Med | "Show all" toggle veya expandable row | S |
| 3 | Portfolio value'nun 24s değişimi (%) yok — tek bir statik sayı gösteriliyor | High | Backend'den 24h change eklenince UI'a yüzdesel değişim + renk (yeşil/kırmızı) ekle | M |
| 4 | AllocationChart'ta "Others" gruplama yok — 8 asset'ten fazlası sessizce kesilir | Med | 7+ asset varsa son dilimi "Others (N)" olarak birleştir | S |
| 5 | Share link listesinde oluşturulma tarihi gösterilmiyor; hangi profil için olduğu etiketlenmiyor | Med | Link card'ına `profile_id → profile name` çözümle, `created_at` göster | S |
| 6 | Mobile'da ProfileSwitcher pill'leri overflow'da horizontal scroll yok — `flex-wrap` ile kırılıyor ama okunaksız olabilir | Med | `overflow-x-auto` ile yatay scroll, `flex-nowrap` | S |
| 7 | Settings sayfasında API key ekleme tarihi dışında hiçbir key metadata yok (exchange logo, status) | Low | Exchange logo/icon (SVG) ve "Last used" opsiyonu | M |

---

### Kesin Olmalı (industry standard)

- **Login sayfası:** Unauthenticated → redirect to `/login`; authenticated → redirect to `/dashboard`
- **Favicon ve OG meta:** `layout.tsx`'de sadece `<title>` ve `<description>` var; `og:image`, `og:type`, favicon eksik
- **Loading/error/empty state üçlüsü:** Her data bölümü için üç durum ayrı tasarlanmalı — şu an bazı yerlerde eksik
- **Tooltip accessibility:** AllocationChart'ta Recharts tooltip'ine `role="tooltip"` ve keyboard focus gerekmez ama en azından içerik okunabilir olmalı
- **Form validation feedback:** AddProfileModal'da sadece submit hatası var; boş submit engellenmiş ama karakter limiti gösterilmiyor
- **Consistent empty states:** Bazı yerlerde icon + açıklama + CTA var, bazı yerlerde sadece plain text

---

### Kesin Değişmeli (mevcut sorunlar)

- `confirm()` native browser dialog → custom modal
- Dashboard header: "CoinHQ" h1 başlığı basit metin — logo veya wordmark olmalı
- Tailwind `theme.extend: {}` boş bırakılmış → design token'lar mutlaka tanımlanmalı, yoksa her bileşen kendi renk kararını veriyor (gray-800 vs gray-850 tutarsızlık riski)
- Settings'de `← Dashboard` link'i stilsiz, küçük ve dikkat çekmiyor
- ProfileSwitcher ve ShareLinkManager'da ayrı ayrı "profile filter" UI var — iki yerde duplicate pattern

---

### Nice-to-Have (diferansiasyon)

- Portfolio value'da animasyonlu sayaç (`countUp` library)
- Dark/light mode toggle (şu an `dark` class hardcode)
- Drag-to-reorder profiles
- Donut chart yerine treemap (daha fazla coin için daha okunabilir)
- Share sayfasında "Powered by CoinHQ" CTA — growth lever
- Dashboard'da "Last synced" live timer
- Keyboard shortcut'lar: `Cmd+K` command palette, sayısal tuşlarla profil geçişi
