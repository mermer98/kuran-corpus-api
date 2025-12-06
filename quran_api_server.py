#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 Quran Corpus REST API Server - Full Version
===============================================
JSON tabanlı tam özellikli API - 6236 ayet, morfoloji, kök arama
"""

import sys
import traceback

print(f"🐍 Python version: {sys.version}")
print(f"📁 Working directory: {__file__}")

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    from functools import wraps
    import json
    import os
    from datetime import datetime
    import re
    print("✓ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

app = Flask(__name__)
CORS(app)

# Configuration
API_VERSION = "2.0.0"
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600

# Rate limiting storage
request_log = {}

# JSON verileri yükle
print("📚 Kuran verileri yükleniyor...")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"📁 Data directory: {DATA_DIR}")

# Dosyaları listele
try:
    files = os.listdir(DATA_DIR)
    print(f"📂 Files in directory: {[f for f in files if f.endswith('.json')]}")
except Exception as e:
    print(f"❌ Cannot list directory: {e}")

# Ana veri dosyaları
try:
    verses_path = os.path.join(DATA_DIR, 'data_verses.json')
    print(f"   Loading: {verses_path}")
    with open(verses_path, 'r', encoding='utf-8') as f:
        verses_data = json.load(f)
        VERSES = verses_data.get('verses', [])
        SURAS = verses_data.get('suras', [])
    print(f"   ✓ {len(VERSES)} ayet yüklendi")
    print(f"   ✓ {len(SURAS)} sure bilgisi yüklendi")
except Exception as e:
    VERSES = []
    SURAS = []
    print(f"   ⚠ Ayet verileri yüklenemedi: {e}")
    traceback.print_exc()

try:
    trans_path = os.path.join(DATA_DIR, 'data_translations.json')
    print(f"   Loading: {trans_path}")
    with open(trans_path, 'r', encoding='utf-8') as f:
        TRANSLATIONS = json.load(f)
    print(f"   ✓ {len(TRANSLATIONS)} meal yüklendi")
except Exception as e:
    TRANSLATIONS = {}
    print(f"   ⚠ Meal verileri yüklenemedi: {e}")

try:
    roots_path = os.path.join(DATA_DIR, 'data_roots.json')
    print(f"   Loading: {roots_path}")
    with open(roots_path, 'r', encoding='utf-8') as f:
        ROOT_INDEX = json.load(f)
    print(f"   ✓ {len(ROOT_INDEX)} kök indeksi yüklendi")
except Exception as e:
    ROOT_INDEX = {}
    print(f"   ⚠ Kök verileri yüklenemedi: {e}")

# Morfoloji verilerini yükle
try:
    morph_path = os.path.join(DATA_DIR, 'data_morphology_compact.json')
    print(f"   Loading: {morph_path}")
    with open(morph_path, 'r', encoding='utf-8') as f:
        MORPHOLOGY = json.load(f)
    print(f"   ✓ {len(MORPHOLOGY)} ayet için morfoloji yüklendi")
except Exception as e:
    MORPHOLOGY = {}
    print(f"   ⚠ Morfoloji verileri yüklenemedi: {e}")

# Çoklu meal verilerini yükle
try:
    multi_trans_path = os.path.join(DATA_DIR, 'data_multi_translations.json')
    print(f"   Loading: {multi_trans_path}")
    with open(multi_trans_path, 'r', encoding='utf-8') as f:
        MULTI_TRANSLATIONS = json.load(f)
    print(f"   ✓ {len(MULTI_TRANSLATIONS)} farklı meal yüklendi")
except Exception as e:
    MULTI_TRANSLATIONS = {}
    print(f"   ⚠ Çoklu meal verileri yüklenemedi: {e}")

# Kelime kelime çeviri yükle
try:
    wbw_path = os.path.join(DATA_DIR, 'data_word_by_word.json')
    print(f"   Loading: {wbw_path}")
    with open(wbw_path, 'r', encoding='utf-8') as f:
        WORD_BY_WORD = json.load(f)
    print(f"   ✓ {len(WORD_BY_WORD)} ayet için kelime kelime çeviri yüklendi")
except Exception as e:
    WORD_BY_WORD = {}
    print(f"   ⚠ Kelime kelime çeviri yüklenemedi: {e}")

# Transliterasyon yükle
try:
    translit_path = os.path.join(DATA_DIR, 'data_transliteration.json')
    print(f"   Loading: {translit_path}")
    with open(translit_path, 'r', encoding='utf-8') as f:
        TRANSLITERATION = json.load(f)
    print(f"   ✓ {len(TRANSLITERATION)} ayet transliterasyonu yüklendi")
except Exception as e:
    TRANSLITERATION = {}
    print(f"   ⚠ Transliterasyon yüklenemedi: {e}")

# Arapça tefsir yükle
try:
    tafsir_path = os.path.join(DATA_DIR, 'data_tafsir_arabic.json')
    print(f"   Loading: {tafsir_path}")
    with open(tafsir_path, 'r', encoding='utf-8') as f:
        TAFSIR_ARABIC = json.load(f)
    print(f"   ✓ {len(TAFSIR_ARABIC)} ayet tefsiri yüklendi")
except Exception as e:
    TAFSIR_ARABIC = {}
    print(f"   ⚠ Arapça tefsir yüklenemedi: {e}")

# Kelime frekansı yükle
try:
    freq_path = os.path.join(DATA_DIR, 'data_word_frequency.json')
    print(f"   Loading: {freq_path}")
    with open(freq_path, 'r', encoding='utf-8') as f:
        WORD_FREQUENCY = json.load(f)
    print(f"   ✓ Kelime frekansı yüklendi")
except Exception as e:
    WORD_FREQUENCY = {}
    print(f"   ⚠ Kelime frekansı yüklenemedi: {e}")

print("✅ Veriler hazır!\n")

# Sure isimlerini hazırla
SURA_NAMES = {s['n']: s['name'] for s in SURAS} if SURAS else {}

class APIResponse:
    @staticmethod
    def success(data, message="Success", status_code=200):
        return jsonify({
            "success": True,
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }), status_code
    
    @staticmethod
    def error(message, error_code="ERROR", status_code=400):
        return jsonify({
            "success": False,
            "status": "error",
            "message": message,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat()
        }), status_code

def check_rate_limit(ip):
    if not RATE_LIMIT_ENABLED:
        return True
    now = datetime.now()
    if ip not in request_log:
        request_log[ip] = []
    request_log[ip] = [t for t in request_log[ip] if (now - t).seconds < RATE_LIMIT_WINDOW]
    if len(request_log[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    request_log[ip].append(now)
    return True

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_rate_limit(request.remote_addr):
            return APIResponse.error("Rate limit exceeded", "RATE_LIMIT_EXCEEDED", 429)
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/')
def home():
    return APIResponse.success({
        "api": "Kuran Corpus API",
        "version": API_VERSION,
        "verses": len(VERSES),
        "suras": len(SURAS),
        "roots": len(ROOT_INDEX),
        "endpoints": ["/api/search", "/api/verse", "/api/sura", "/api/root", "/api/stats"]
    }, "Kuran Corpus API is running!")

@app.route('/api/health')
def health():
    return APIResponse.success({
        "status": "healthy",
        "verses_loaded": len(VERSES),
        "translations_loaded": len(TRANSLATIONS),
        "roots_loaded": len(ROOT_INDEX)
    })

@app.route('/api/demo')
def demo():
    return APIResponse.success({
        "message": "Full Kuran API is running!",
        "total_verses": len(VERSES),
        "total_suras": len(SURAS),
        "total_roots": len(ROOT_INDEX),
        "features": ["Full Search", "Root Search", "Morphology", "Multi-Translation"]
    })

@app.route('/api/stats')
@rate_limit
def stats():
    """Kuran istatistikleri"""
    return APIResponse.success({
        "total_suras": 114,
        "total_verses": len(VERSES),
        "total_words": 77845,
        "unique_roots": len(ROOT_INDEX),
        "translations": 1,
        "suras": SURAS[:10]  # İlk 10 sure
    })

@app.route('/api/search')
@rate_limit  
def search():
    """Tam metin arama - Arapça ve Türkçe"""
    query = request.args.get('q', request.args.get('query', '')).strip()
    search_type = request.args.get('type', 'word').lower()
    limit = min(int(request.args.get('limit', 50)), 200)
    
    if not query or len(query) < 2:
        return APIResponse.error("Query must be at least 2 characters", "INVALID_INPUT", 400)
    
    results = []
    query_lower = query.lower()
    
    # Kök araması
    if search_type == 'root':
        if query in ROOT_INDEX:
            refs = ROOT_INDEX[query][:limit]
            for ref in refs:
                parts = ref.split(':')
                if len(parts) == 2:
                    sura, verse = int(parts[0]), int(parts[1])
                    verse_data = get_verse_data(sura, verse)
                    if verse_data:
                        verse_data['root'] = query
                        results.append(verse_data)
    else:
        # Türkçe meal araması
        for key, meal in TRANSLATIONS.items():
            if query_lower in meal.lower():
                parts = key.split(':')
                if len(parts) == 2:
                    sura, verse = int(parts[0]), int(parts[1])
                    verse_data = get_verse_data(sura, verse)
                    if verse_data:
                        # Aranan kelimeyi vurgula
                        verse_data['match_type'] = 'translation'
                        results.append(verse_data)
                        if len(results) >= limit:
                            break
        
        # Arapça metin araması
        if len(results) < limit:
            for v in VERSES:
                if query in v.get('t', ''):
                    verse_data = get_verse_data(v['s'], v['a'])
                    if verse_data:
                        verse_data['match_type'] = 'arabic'
                        results.append(verse_data)
                        if len(results) >= limit:
                            break
    
    return APIResponse.success({
        "query": query,
        "type": search_type,
        "count": len(results),
        "results": results
    }, f"Found {len(results)} results for '{query}'")

@app.route('/api/verse/<int:sura>/<int:verse>')
@rate_limit
def get_verse(sura, verse):
    """Belirli bir ayet getir"""
    verse_data = get_verse_data(sura, verse)
    if verse_data:
        return APIResponse.success(verse_data)
    return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)

@app.route('/api/sura/<int:sura_num>')
@rate_limit
def get_sura(sura_num):
    """Belirli bir sure getir"""
    if sura_num < 1 or sura_num > 114:
        return APIResponse.error("Sura number must be between 1-114", "INVALID_INPUT", 400)
    
    sura_verses = [v for v in VERSES if v['s'] == sura_num]
    sura_info = next((s for s in SURAS if s['n'] == sura_num), None)
    
    verses = []
    for v in sura_verses:
        key = f"{v['s']}:{v['a']}"
        verses.append({
            "verse_number": v['a'],
            "arabic": v['t'],
            "turkish": TRANSLATIONS.get(key, ""),
            "reference": key
        })
    
    return APIResponse.success({
        "sura_number": sura_num,
        "name": sura_info['name'] if sura_info else f"Sure {sura_num}",
        "verse_count": len(verses),
        "verses": verses
    })

@app.route('/api/root/<root>')
@rate_limit
def get_root(root):
    """Kök araması"""
    if root not in ROOT_INDEX:
        return APIResponse.error(f"Root '{root}' not found", "NOT_FOUND", 404)
    
    refs = ROOT_INDEX[root]
    results = []
    for ref in refs[:50]:
        parts = ref.split(':')
        if len(parts) == 2:
            verse_data = get_verse_data(int(parts[0]), int(parts[1]))
            if verse_data:
                results.append(verse_data)
    
    return APIResponse.success({
        "root": root,
        "count": len(refs),
        "verses": results
    })

@app.route('/api/roots')
@rate_limit
def list_roots():
    """Tüm kökleri listele"""
    roots = list(ROOT_INDEX.keys())
    return APIResponse.success({
        "total": len(roots),
        "roots": sorted(roots)[:100]  # İlk 100
    })

@app.route('/api/random')
@rate_limit
def random_verse():
    """Rastgele ayet"""
    import random
    if VERSES:
        v = random.choice(VERSES)
        return APIResponse.success(get_verse_data(v['s'], v['a']))
    return APIResponse.error("No verses available")

@app.route('/api/suras')
@rate_limit
def list_suras():
    """Tüm sureleri listele"""
    return APIResponse.success({
        "total": len(SURAS),
        "suras": SURAS
    })

@app.route('/api/morphology/<int:sura>/<int:verse>')
@rate_limit
def get_morphology(sura, verse):
    """Morfolojik analiz - gerçek verilerle"""
    verse_data = get_verse_data(sura, verse)
    if not verse_data:
        return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)
    
    key = f"{sura}:{verse}"
    arabic_text = verse_data['arabic']
    arabic_words = arabic_text.split()
    
    # Lemma temizleme fonksiyonu
    def clean_lemma(lemma):
        """Lemma'daki özel karakterleri temizle"""
        if not lemma:
            return ''
        # Baştaki , { ve } karakterlerini temizle
        return lemma.lstrip(',{').rstrip('}')
    
    # POS etiketlerini Türkçeye çevir
    pos_translations = {
        'N': 'İsim', 'V': 'Fiil', 'ADJ': 'Sıfat', 'PN': 'Özel İsim',
        'P': 'Edat', 'PRON': 'Zamir', 'DET': 'Belirleyici', 'CONJ': 'Bağlaç',
        'PART': 'Parçacık', 'ADV': 'Zarf', 'INTJ': 'Ünlem',
        'P+N': 'Edat+İsim', 'DET+N': 'Belirleyici+İsim', 'DET+ADJ': 'Belirleyici+Sıfat',
        'PRON+V': 'Zamir+Fiil', 'CONJ+V': 'Bağlaç+Fiil'
    }
    
    def get_pos_display(pos):
        """POS etiketini hem İngilizce hem Türkçe göster"""
        tr = pos_translations.get(pos, '')
        return f"{pos} ({tr})" if tr else pos
    
    # Morfoloji verisini kontrol et
    if key in MORPHOLOGY:
        morph_data = MORPHOLOGY[key]
        segments = []
        
        for i, word_info in enumerate(morph_data):
            # Arapça kelimeyi orijinal metinden al (daha okunabilir)
            arabic_word = arabic_words[i] if i < len(arabic_words) else word_info.get('w', '')
            raw_pos = word_info.get('p', 'WORD')
            
            segments.append({
                "position": i + 1,
                "segment": arabic_word,
                "buckwalter": word_info.get('w', ''),
                "root": word_info.get('r', '—'),
                "lemma": clean_lemma(word_info.get('l', '')),
                "pos": raw_pos,
                "pos_display": get_pos_display(raw_pos)
            })
        
        return APIResponse.success({
            "reference": verse_data['reference'],
            "surah_name": verse_data['surah_name'],
            "arabic": arabic_text,
            "turkish": verse_data['turkish'],
            "word_count": len(segments),
            "segments": segments,
            "has_morphology": True
        })
    else:
        # Morfoloji verisi yoksa basit ayrıştırma
        segments = []
        for i, word in enumerate(arabic_words):
            segments.append({
                "position": i + 1,
                "segment": word,
                "root": "—",
                "pos": "WORD",
                "lemma": word
            })
        
        return APIResponse.success({
            "reference": verse_data['reference'],
            "surah_name": verse_data['surah_name'],
            "arabic": arabic_text,
            "turkish": verse_data['turkish'],
            "word_count": len(segments),
            "segments": segments,
            "has_morphology": False
        })

# ============================================================================
# ÇOKLU MEAL ENDPOİNT'İ
# ============================================================================

@app.route('/api/translations/<int:sura>/<int:verse>')
@rate_limit
def get_multi_translations(sura, verse):
    """Çoklu meal karşılaştırma"""
    verse_data = get_verse_data(sura, verse)
    if not verse_data:
        return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)
    
    key = f"{sura}:{verse}"
    translations_list = []
    
    for code, data in MULTI_TRANSLATIONS.items():
        if key in data.get('verses', {}):
            translations_list.append({
                "code": code,
                "name": data['name'],
                "short": data['short'],
                "text": data['verses'][key]
            })
    
    return APIResponse.success({
        "reference": verse_data['reference'],
        "surah_name": verse_data['surah_name'],
        "arabic": verse_data['arabic'],
        "translation_count": len(translations_list),
        "translations": translations_list
    })

@app.route('/api/translations/list')
@rate_limit
def list_translations():
    """Mevcut mealleri listele"""
    translations_info = []
    for code, data in MULTI_TRANSLATIONS.items():
        translations_info.append({
            "code": code,
            "name": data['name'],
            "short": data['short'],
            "verse_count": len(data.get('verses', {}))
        })
    
    return APIResponse.success({
        "count": len(translations_info),
        "translations": translations_info
    })

# ============================================================================
# KELİME KELİME ÇEVİRİ ENDPOİNT'İ
# ============================================================================

@app.route('/api/word-by-word/<int:sura>/<int:verse>')
@rate_limit
def get_word_by_word(sura, verse):
    """Kelime kelime Türkçe çeviri"""
    verse_data = get_verse_data(sura, verse)
    if not verse_data:
        return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)
    
    key = f"{sura}:{verse}"
    arabic_words = verse_data['arabic'].split()
    
    wbw_list = WORD_BY_WORD.get(key, [])
    
    # Morfoloji verisini de ekle
    morph_data = MORPHOLOGY.get(key, [])
    
    words = []
    for i, arabic in enumerate(arabic_words):
        word_info = {
            "position": i + 1,
            "arabic": arabic,
            "turkish": wbw_list[i]['t'] if i < len(wbw_list) else "",
        }
        # Morfoloji varsa ekle
        if i < len(morph_data):
            word_info["root"] = morph_data[i].get('r', '')
            word_info["pos"] = morph_data[i].get('p', '')
        words.append(word_info)
    
    return APIResponse.success({
        "reference": verse_data['reference'],
        "surah_name": verse_data['surah_name'],
        "arabic": verse_data['arabic'],
        "turkish": verse_data['turkish'],
        "word_count": len(words),
        "words": words
    })

# ============================================================================
# TRANSLİTERASYON ENDPOİNT'İ
# ============================================================================

@app.route('/api/transliteration/<int:sura>/<int:verse>')
@rate_limit
def get_transliteration(sura, verse):
    """Ayet transliterasyonu (Latin harfli okunuş)"""
    verse_data = get_verse_data(sura, verse)
    if not verse_data:
        return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)
    
    key = f"{sura}:{verse}"
    translit = TRANSLITERATION.get(key, "")
    
    return APIResponse.success({
        "reference": verse_data['reference'],
        "surah_name": verse_data['surah_name'],
        "arabic": verse_data['arabic'],
        "transliteration": translit,
        "turkish": verse_data['turkish']
    })

# ============================================================================
# ARAPÇA TEFSİR ENDPOİNT'İ
# ============================================================================

@app.route('/api/tafsir/<int:sura>/<int:verse>')
@rate_limit
def get_tafsir(sura, verse):
    """Arapça tefsir (Müyesser)"""
    verse_data = get_verse_data(sura, verse)
    if not verse_data:
        return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)
    
    key = f"{sura}:{verse}"
    tafsir = TAFSIR_ARABIC.get(key, "")
    
    return APIResponse.success({
        "reference": verse_data['reference'],
        "surah_name": verse_data['surah_name'],
        "arabic": verse_data['arabic'],
        "tafsir_arabic": tafsir,
        "turkish": verse_data['turkish']
    })

# ============================================================================
# KELİME FREKANSI ENDPOİNT'İ
# ============================================================================

@app.route('/api/frequency')
@rate_limit
def get_word_frequency():
    """En sık kullanılan kelimeler"""
    limit = request.args.get('limit', 100, type=int)
    limit = min(limit, 500)  # Max 500
    
    top_words = WORD_FREQUENCY.get('top_words', [])[:limit]
    
    return APIResponse.success({
        "count": len(top_words),
        "words": top_words
    })

# ============================================================================
# DETAYLI AYET BİLGİSİ (TÜM VERİLER)
# ============================================================================

@app.route('/api/verse-full/<int:sura>/<int:verse>')
@rate_limit
def get_verse_full(sura, verse):
    """Ayetin tüm detayları - tek endpoint'te"""
    verse_data = get_verse_data(sura, verse)
    if not verse_data:
        return APIResponse.error(f"Verse {sura}:{verse} not found", "NOT_FOUND", 404)
    
    key = f"{sura}:{verse}"
    arabic_words = verse_data['arabic'].split()
    
    # Kelime kelime çeviri
    wbw_list = WORD_BY_WORD.get(key, [])
    
    # Morfoloji
    morph_data = MORPHOLOGY.get(key, [])
    
    # Kelime detayları
    words = []
    for i, arabic in enumerate(arabic_words):
        word_info = {
            "position": i + 1,
            "arabic": arabic,
            "turkish": wbw_list[i]['t'] if i < len(wbw_list) else "",
        }
        if i < len(morph_data):
            word_info["root"] = morph_data[i].get('r', '')
            word_info["lemma"] = morph_data[i].get('l', '').lstrip(',{')
            word_info["pos"] = morph_data[i].get('p', '')
        words.append(word_info)
    
    # Çoklu mealler
    translations = []
    for code, data in MULTI_TRANSLATIONS.items():
        if key in data.get('verses', {}):
            translations.append({
                "name": data['short'],
                "text": data['verses'][key]
            })
    
    return APIResponse.success({
        "reference": verse_data['reference'],
        "surah_name": verse_data['surah_name'],
        "arabic": verse_data['arabic'],
        "turkish": verse_data['turkish'],
        "transliteration": TRANSLITERATION.get(key, ""),
        "tafsir_arabic": TAFSIR_ARABIC.get(key, ""),
        "word_count": len(words),
        "words": words,
        "translations": translations
    })

# Helper function
def get_verse_data(sura, verse):
    """Ayet verisini hazırla"""
    v = next((x for x in VERSES if x['s'] == sura and x['a'] == verse), None)
    if not v:
        return None
    
    key = f"{sura}:{verse}"
    return {
        "reference": key,
        "sura": sura,
        "verse_number": verse,
        "surah_name": SURA_NAMES.get(sura, f"Sure {sura}"),
        "arabic": v['t'],
        "turkish": TRANSLATIONS.get(key, ""),
        "type": "verse"
    }

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Kuran Corpus API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
