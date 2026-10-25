# Kur'an Corpus API

Kur'an üzerinde araştırma yapmak için hazırlanmış küçük bir REST API (Python + Flask). Ayetler, mealler, kelime kelime anlamlar, kökler, morfoloji, okunuş, tefsir ve kelime sıklığı verilerini JSON olarak sunar. Veriler `data_*.json` dosyalarından okunur, ayrı bir veritabanı gerekmez.

İki basit web arayüzü de vardır: `web_frontend.html` ve `advanced_web_frontend.html`.

## Çalıştırma
```
pip install -r requirements.txt
python quran_api_server.py
```
Sunucu `http://localhost:5000` adresinde açılır. `PORT` ortam değişkeniyle port değiştirilebilir. `render.yaml` ve `Procfile` ile Render gibi servislere kurulabilir.

## Uç noktalar
| Adres | Ne yapar |
|---|---|
| `/api/health`, `/api/stats`, `/api/demo` | Durum, istatistik, örnek |
| `/api/search?q=...` | Arama |
| `/api/verse/<sure>/<ayet>` | Tek ayet |
| `/api/verse-full/<sure>/<ayet>` | Ayetin tüm verileri bir arada |
| `/api/sura/<no>`, `/api/suras` | Sure ve sure listesi |
| `/api/random` | Rastgele ayet |
| `/api/root/<kök>`, `/api/roots` | Kök arama ve kök listesi |
| `/api/morphology/<sure>/<ayet>` | Morfolojik analiz |
| `/api/translations/<sure>/<ayet>`, `/api/translations/list` | Mealler |
| `/api/word-by-word/<sure>/<ayet>` | Kelime kelime anlam |
| `/api/transliteration/<sure>/<ayet>` | Okunuş |
| `/api/tafsir/<sure>/<ayet>` | Arapça tefsir |
| `/api/frequency` | Kelime sıklığı |

Örnek: `http://localhost:5000/api/verse/1/1`

## Veri
`data_*.json` dosyaları depoda hazır gelir (toplam yaklaşık 20 MB). Kaynakların ve meal metinlerinin hakları ilgili sahiplerine aittir.
