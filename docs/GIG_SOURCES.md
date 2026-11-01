# Gig kaynakları: durum raporu

Bu rapor `jobradar gig validate` komutunun gerçek bir taramadan ürettiği çıktıdır (1 Kasım 2026). Her kaynak için dokuz kontrol çalıştırılır: erişim, ilan listesi, ilan detayı, orijinal bağlantı, ilan tarihi, ödeme bilgisi, Ankara filtresi, tekilleştirme ve tekrar taramada yeni ilan yakalama.

Raporu yenilemek için: `uv run jobradar gig validate`

| Kaynak | Durum | Yöntem | Son hata |
|---|---|---|---|
| Eleman.net (Ankara) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Eleman.net (günlük eleman, tüm Türkiye) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| İşin Olsun (Ankara) | working | HTTP (liste sayfası + ilan sayfası, 3 liste) | - |
| Telegram: Ankara İş İlanları | working | HTTP (kanalın herkese açık web önizlemesi) | - |
| R10 (iş ilanları forumu) | working | HTTP (liste sayfası + ilan sayfası, 2 liste) | - |
| Upwork (Turkish jobs) | blocked | HTTP (liste sayfası + ilan sayfası, 2 liste) | www.upwork.com answered 403 |
| DataForce Community (projects) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| OneForma (open projects) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| RWS TrainAI | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | www.rws.com answered 404 |
| OpenTrain AI (Türkiye jobs) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Bionluk (iş arayan) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Armut (hizmet verenler) | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | armut.com answered 404 |
| Facebook grupları (iş ilanı) | manual | manuel (kullanıcı ilanı ekler) | - |
| WhatsApp grupları (iş ilanı) | manual | manuel (kullanıcı ilanı ekler) | - |
| Sahibinden (Ankara) | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | www.sahibinden.com answered 403 |
| Kariyer.net (part-time, Ankara) | blocked | HTTP (liste sayfası + ilan sayfası, 2 liste) | www.kariyer.net answered 403 |
| SecretCV (Ankara, part-time) | working | HTTP (liste sayfası + ilan sayfası, 2 liste) | - |
| Indeed (Ankara, part-time) | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | tr.indeed.com answered 403 |
| LinkedIn (public job search, Ankara) | blocked | HTTP (liste sayfası + ilan sayfası, 2 liste) | robots.txt disallows https://www.linkedin.com/jobs/search/?keywords=Part-Time&location=Ankara&f_TPR=r86400 |
| Ankara Büyükşehir Belediyesi Kariyer Merkezi | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| R10 (iş arayanlar) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Contra (freelance jobs) | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Mindrift (annotation projects) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Corpshore (Türkiye) | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Rise Data Labs (remote AI jobs) | working | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| TELUS Digital (careers) | blocked | HTTP (liste sayfası + ilan sayfası, 1 liste) | - |
| Telegram: Eleman Arayanlar | working | HTTP (kanalın herkese açık web önizlemesi) | - |
| Telegram: Rasyonel Kariyer | blocked | HTTP (kanalın herkese açık web önizlemesi) | rasyokariyer has no public preview |

## Özet

Özet: 14 çalışıyor, 12 engelli, 0 hata verdi, 2 manuel.

Engelli kaynaklarda hiçbir koruma mekanizması atlanmaz: 403, bot challenge sayfası, robots.txt yasağı veya olmayan sayfa olduğu gibi raporlanır. LinkedIn'in robots.txt'i generic ajanlara her yolu kapatıyor (User-agent: * -> Disallow: /) ve tarayıcı izin istiyor; Facebook ve WhatsApp grupları taranmaz, ilanlar kullanıcının getirdiği metinle eklenir.

## Kaynakların tam çıktısı

```
Eleman.net (Ankara)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:24:47.243529Z · hata: 0 · toplam ilan: 60 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 30 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu? https://www.eleman.net/is-ilanlari/ankara
    ✓ İlan listesi alınabiliyor mu? 30 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 2/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 5/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Eleman.net (günlük eleman, tüm Türkiye)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:24:54.236563Z · hata: 0 · toplam ilan: 60 · kısa süreli iş: 1 · son 24 saatte bulunan ilan: 30 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu? https://www.eleman.net/is-ilanlari/gunluk-eleman
    ✓ İlan listesi alınabiliyor mu? 30 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 1/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 5/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

İşin Olsun (Ankara)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 3 liste)
  son başarılı tarama: 2026-11-01T14:25:05.495786Z · hata: 0 · toplam ilan: 250 · kısa süreli iş: 2 · son 24 saatte bulunan ilan: 125 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu? https://isinolsun.com/is-ilanlari/ankara
    ✓ İlan listesi alınabiliyor mu? 126 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 2/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 4/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 5/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Telegram: Ankara İş İlanları  [working]
  yöntem: HTTP (kanalın herkese açık web önizlemesi)
  son başarılı tarama: 2026-11-01T14:25:12.626320Z · hata: 0 · toplam ilan: 28 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 10 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu?
    ✓ İlan listesi alınabiliyor mu? 14 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✗ İlan tarihi çıkarılabiliyor mu? 0/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 1/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 2/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

R10 (iş ilanları forumu)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 2 liste)
  son başarılı tarama: 2026-11-01T14:25:21.277957Z · hata: 0 · toplam ilan: 106 · kısa süreli iş: 2 · son 24 saatte bulunan ilan: 50 · doğrulamada sınıflandırılan: 0
  not: The forum carries the ads; the blog page lists articles, not ads.
    ✓ Kaynağa erişilebiliyor mu? https://www.r10.net/yazilim-kodlama-is-ilanlari/
    ✓ İlan listesi alınabiliyor mu? 53 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 1/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 2/5 ilanda ödeme modeli var
    ✗ Ankara filtresi uygulanabiliyor mu? 0/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Upwork (Turkish jobs)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 2 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: Answers a bot challenge page.
  son hata: www.upwork.com answered 403
    ✗ Kaynağa erişilebiliyor mu? www.upwork.com answered 403
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

DataForce Community (projects)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:25:29.785174Z · hata: 0 · toplam ilan: 18 · kısa süreli iş: 1 · son 24 saatte bulunan ilan: 2 · doğrulamada sınıflandırılan: 2
    ✓ Kaynağa erişilebiliyor mu? https://dataforcecommunity.transperfect.com/projects
    ✓ İlan listesi alınabiliyor mu? 9 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✗ İlan tarihi çıkarılabiliyor mu? 0/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 2/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 4/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 2 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

OneForma (open projects)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:25:37.550692Z · hata: 0 · toplam ilan: 24 · kısa süreli iş: 1 · son 24 saatte bulunan ilan: 12 · doğrulamada sınıflandırılan: 2
    ✓ Kaynağa erişilebiliyor mu? https://www.oneforma.com/projects/
    ✓ İlan listesi alınabiliyor mu? 12 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 2/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 1/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

RWS TrainAI  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: The page answers 404; RWS moved the programme.
  son hata: www.rws.com answered 404
    ✗ Kaynağa erişilebiliyor mu? www.rws.com answered 404
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

OpenTrain AI (Türkiye jobs)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:25:46.579437Z · hata: 0 · toplam ilan: 72 · kısa süreli iş: 20 · son 24 saatte bulunan ilan: 20 · doğrulamada sınıflandırılan: 5
    ✓ Kaynağa erişilebiliyor mu? https://www.opentrain.ai/jobs/country/turkiye/
    ✓ İlan listesi alınabiliyor mu? 36 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 5/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 5/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Bionluk (iş arayan)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:25:53.714463Z · hata: 0 · toplam ilan: 18 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 9 · doğrulamada sınıflandırılan: 0
  not: The job board itself is behind a login; this page lists the open briefs.
    ✓ Kaynağa erişilebiliyor mu? https://bionluk.com/freelancer-bul
    ✓ İlan listesi alınabiliyor mu? 9 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✗ Ödeme bilgisi çıkarılabiliyor mu? 0/5 ilanda ödeme modeli var
    ✗ Ankara filtresi uygulanabiliyor mu? 0/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Armut (hizmet verenler)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: No public job list over HTTP; the site renders it with JavaScript.
  son hata: armut.com answered 404
    ✗ Kaynağa erişilebiliyor mu? armut.com answered 404
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

Facebook grupları (iş ilanı)  [manual]
  yöntem: manuel (kullanıcı ilanı ekler)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: Facebook has no public listing API and groups need an account; nothing is scraped. Gruplar: https://www.facebook.com/groups/1533399140233390, https://www.facebook.com/search/groups/?q=ankara%20g%C3%BCnl%C3%BCk%20i%C5%9F%20ilanlar%C4%B1
    - Kaynağa erişilebiliyor mu? kullanıcı girişi gerekiyor
    - İlan listesi alınabiliyor mu? kullanıcı girişi gerekiyor
    - İlan detayları okunabiliyor mu? kullanıcı girişi gerekiyor
    - Orijinal ilan bağlantısı alınabiliyor mu? kullanıcı girişi gerekiyor
    - İlan tarihi çıkarılabiliyor mu? kullanıcı girişi gerekiyor
    - Ödeme bilgisi çıkarılabiliyor mu? kullanıcı girişi gerekiyor
    - Ankara filtresi uygulanabiliyor mu? kullanıcı girişi gerekiyor
    - Sonuçlar tekilleştirilebiliyor mu? kullanıcı girişi gerekiyor
    - Tekrar taramada yeni ilan yakalanıyor mu? kullanıcı girişi gerekiyor

WhatsApp grupları (iş ilanı)  [manual]
  yöntem: manuel (kullanıcı ilanı ekler)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: Groups need a membership and the messages are not public; nothing is scraped. Gruplar: https://whatsappgruplari.com/grup/ankara-is-ilanlari, https://whatsappgruplari.com/kategori/is-ilanlari, https://whatsappkanali.com/sehir/ankara/is-ilanlari
    - Kaynağa erişilebiliyor mu? kullanıcı girişi gerekiyor
    - İlan listesi alınabiliyor mu? kullanıcı girişi gerekiyor
    - İlan detayları okunabiliyor mu? kullanıcı girişi gerekiyor
    - Orijinal ilan bağlantısı alınabiliyor mu? kullanıcı girişi gerekiyor
    - İlan tarihi çıkarılabiliyor mu? kullanıcı girişi gerekiyor
    - Ödeme bilgisi çıkarılabiliyor mu? kullanıcı girişi gerekiyor
    - Ankara filtresi uygulanabiliyor mu? kullanıcı girişi gerekiyor
    - Sonuçlar tekilleştirilebiliyor mu? kullanıcı girişi gerekiyor
    - Tekrar taramada yeni ilan yakalanıyor mu? kullanıcı girişi gerekiyor

Sahibinden (Ankara)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  son hata: www.sahibinden.com answered 403
    ✗ Kaynağa erişilebiliyor mu? www.sahibinden.com answered 403
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

Kariyer.net (part-time, Ankara)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 2 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  son hata: www.kariyer.net answered 403
    ✗ Kaynağa erişilebiliyor mu? www.kariyer.net answered 403
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

SecretCV (Ankara, part-time)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 2 liste)
  son başarılı tarama: 2026-11-01T14:26:18.708135Z · hata: 0 · toplam ilan: 82 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 41 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu? https://www.secretcv.com/is-ilanlari/ankara-is-ilanlari
    ✓ İlan listesi alınabiliyor mu? 41 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✗ Ödeme bilgisi çıkarılabiliyor mu? 0/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 5/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Indeed (Ankara, part-time)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  son hata: tr.indeed.com answered 403
    ✗ Kaynağa erişilebiliyor mu? tr.indeed.com answered 403
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

LinkedIn (public job search, Ankara)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 2 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: LinkedIn's robots.txt disallows every path for generic agents (User-agent: * -> Disallow: /) and asks crawlers to apply for a whitelist, so this source stays blocked until they say yes.
  son hata: robots.txt disallows https://www.linkedin.com/jobs/search/?keywords=Part-Time&location=Ankara&f_TPR=r86400
    ✗ Kaynağa erişilebiliyor mu? robots.txt disallows https://www.linkedin.com/jobs/search/?keywords=Part-Time&location=Ankara&f_TPR=r86400
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

Ankara Büyükşehir Belediyesi Kariyer Merkezi  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu? https://kariyermerkezi.ankara.bel.tr/ilan
    ✗ İlan listesi alınabiliyor mu? 0 ilan
    - Orijinal ilan bağlantısı alınabiliyor mu? ilan yok
    - İlan tarihi çıkarılabiliyor mu? ilan yok
    - Ödeme bilgisi çıkarılabiliyor mu? ilan yok
    - Ankara filtresi uygulanabiliyor mu? ilan yok
    - Sonuçlar tekilleştirilebiliyor mu? ilan yok
    - Tekrar taramada yeni ilan yakalanıyor mu? ilan yok

R10 (iş arayanlar)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:26:27.985800Z · hata: 0 · toplam ilan: 88 · kısa süreli iş: 3 · son 24 saatte bulunan ilan: 40 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu? https://www.r10.net/is-arayanlar/
    ✓ İlan listesi alınabiliyor mu? 44 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✗ İlan tarihi çıkarılabiliyor mu? 0/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 1/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 2/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Contra (freelance jobs)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: The list is rendered with JavaScript.
    ✓ Kaynağa erişilebiliyor mu? https://contra.com/features/find-freelance-jobs
    ✗ İlan listesi alınabiliyor mu? 0 ilan
    - Orijinal ilan bağlantısı alınabiliyor mu? ilan yok
    - İlan tarihi çıkarılabiliyor mu? ilan yok
    - Ödeme bilgisi çıkarılabiliyor mu? ilan yok
    - Ankara filtresi uygulanabiliyor mu? ilan yok
    - Sonuçlar tekilleştirilebiliyor mu? ilan yok
    - Tekrar taramada yeni ilan yakalanıyor mu? ilan yok

Mindrift (annotation projects)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:26:32.718114Z · hata: 0 · toplam ilan: 2 · kısa süreli iş: 1 · son 24 saatte bulunan ilan: 1 · doğrulamada sınıflandırılan: 1
    ✓ Kaynağa erişilebiliyor mu? https://mindrift.ai/project/annotation
    ✓ İlan listesi alınabiliyor mu? 1 ilan
    ✓ İlan detayları okunabiliyor mu? 1/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 1/5
    ✗ İlan tarihi çıkarılabiliyor mu? 0/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 1/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 1/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 1 ilan, 1 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Corpshore (Türkiye)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: The list is rendered with JavaScript.
    ✓ Kaynağa erişilebiliyor mu? https://platform.corpshore.ai/turkiye
    ✗ İlan listesi alınabiliyor mu? 0 ilan
    - Orijinal ilan bağlantısı alınabiliyor mu? ilan yok
    - İlan tarihi çıkarılabiliyor mu? ilan yok
    - Ödeme bilgisi çıkarılabiliyor mu? ilan yok
    - Ankara filtresi uygulanabiliyor mu? ilan yok
    - Sonuçlar tekilleştirilebiliyor mu? ilan yok
    - Tekrar taramada yeni ilan yakalanıyor mu? ilan yok

Rise Data Labs (remote AI jobs)  [working]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: 2026-11-01T14:26:42.424631Z · hata: 0 · toplam ilan: 236 · kısa süreli iş: 2 · son 24 saatte bulunan ilan: 113 · doğrulamada sınıflandırılan: 5
  not: The list is rendered with JavaScript.
    ✓ Kaynağa erişilebiliyor mu? https://experts.risedatalabs.com/jobs
    ✓ İlan listesi alınabiliyor mu? 118 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✓ İlan tarihi çıkarılabiliyor mu? 5/5 ilanda tarih var
    ✓ Ödeme bilgisi çıkarılabiliyor mu? 5/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 5/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 5 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

TELUS Digital (careers)  [blocked]
  yöntem: HTTP (liste sayfası + ilan sayfası, 1 liste)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  not: Answers a Cloudflare block page.
    ✓ Kaynağa erişilebiliyor mu? https://www.telusdigital.com/careers
    ✗ İlan listesi alınabiliyor mu? 0 ilan
    - Orijinal ilan bağlantısı alınabiliyor mu? ilan yok
    - İlan tarihi çıkarılabiliyor mu? ilan yok
    - Ödeme bilgisi çıkarılabiliyor mu? ilan yok
    - Ankara filtresi uygulanabiliyor mu? ilan yok
    - Sonuçlar tekilleştirilebiliyor mu? ilan yok
    - Tekrar taramada yeni ilan yakalanıyor mu? ilan yok

Telegram: Eleman Arayanlar  [working]
  yöntem: HTTP (kanalın herkese açık web önizlemesi)
  son başarılı tarama: 2026-11-01T14:26:50.044191Z · hata: 0 · toplam ilan: 40 · kısa süreli iş: 1 · son 24 saatte bulunan ilan: 6 · doğrulamada sınıflandırılan: 0
    ✓ Kaynağa erişilebiliyor mu?
    ✓ İlan listesi alınabiliyor mu? 20 ilan
    ✓ İlan detayları okunabiliyor mu? 5/5 ilan okundu
    ✓ Orijinal ilan bağlantısı alınabiliyor mu? 5/5
    ✗ İlan tarihi çıkarılabiliyor mu? 0/5 ilanda tarih var
    ✗ Ödeme bilgisi çıkarılabiliyor mu? 0/5 ilanda ödeme modeli var
    ✓ Ankara filtresi uygulanabiliyor mu? 1/5 ilanda yer bilgisi var
    ✓ Sonuçlar tekilleştirilebiliyor mu? 5 ilan, 2 farklı parmak izi
    ✓ Tekrar taramada yeni ilan yakalanıyor mu? ikinci taramada 0 yeni ilan (0 olmalı)

Telegram: Rasyonel Kariyer  [blocked]
  yöntem: HTTP (kanalın herkese açık web önizlemesi)
  son başarılı tarama: hiç · hata: 0 · toplam ilan: 0 · kısa süreli iş: 0 · son 24 saatte bulunan ilan: 0 · doğrulamada sınıflandırılan: 0
  son hata: rasyokariyer has no public preview
    ✗ Kaynağa erişilebiliyor mu? rasyokariyer has no public preview
    - İlan detayları okunabiliyor mu? kaynak okunamadı
    - Orijinal ilan bağlantısı alınabiliyor mu? kaynak okunamadı
    - İlan tarihi çıkarılabiliyor mu? kaynak okunamadı
    - Ödeme bilgisi çıkarılabiliyor mu? kaynak okunamadı
    - Ankara filtresi uygulanabiliyor mu? kaynak okunamadı
    - Sonuçlar tekilleştirilebiliyor mu? kaynak okunamadı
    - Tekrar taramada yeni ilan yakalanıyor mu? kaynak okunamadı

Özet: 14 çalışıyor, 12 engelli, 0 hata verdi, 2 manuel.
```
