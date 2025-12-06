#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 Quran Corpus REST API Server - Full Version
===============================================
JSON tabanlı tam özellikli API - 6236 ayet, morfoloji, kök arama
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import json
import os
from datetime import datetime
import re

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

# Ana veri dosyaları
try:
    with open(os.path.join(DATA_DIR, 'data_verses.json'), 'r', encoding='utf-8') as f:
        verses_data = json.load(f)
        VERSES = verses_data.get('verses', [])
        SURAS = verses_data.get('suras', [])
    print(f"   ✓ {len(VERSES)} ayet yüklendi")
    print(f"   ✓ {len(SURAS)} sure bilgisi yüklendi")
except:
    VERSES = []
    SURAS = []
    print("   ⚠ Ayet verileri yüklenemedi")

try:
    with open(os.path.join(DATA_DIR, 'data_translations.json'), 'r', encoding='utf-8') as f:
        TRANSLATIONS = json.load(f)
    print(f"   ✓ {len(TRANSLATIONS)} meal yüklendi")
except:
    TRANSLATIONS = {}
    print("   ⚠ Meal verileri yüklenemedi")

try:
    with open(os.path.join(DATA_DIR, 'data_roots.json'), 'r', encoding='utf-8') as f:
        ROOT_INDEX = json.load(f)
    print(f"   ✓ {len(ROOT_INDEX)} kök indeksi yüklendi")
except:
    ROOT_INDEX = {}
    print("   ⚠ Kök verileri yüklenemedi")

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
