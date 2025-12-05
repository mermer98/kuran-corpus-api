#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 Quran Corpus REST API Server
================================

Flask tabanlı REST API sunucusu tüm Corpus Kuran özellikleri için.
- 📚 Ayet verisi (10 meal, 8 font, morfoloji)
- 🔍 Arama (semantic, morphology, analytics)
- 📊 Analytics (istatistik, clustering, topic modeling)
- 💾 Export (JSON, CSV)
- 🔐 Authentication & Rate Limiting
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import threading

# Advanced features imports
try:
    from advanced_analytics import AdvancedAnalytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Configuration
API_VERSION = "1.0.0"
DB_PATH = "quran_dictionary.db"
API_KEY_REQUIRED = False  # Token gerektirme (opsiyonel)
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600  # 1 saat

# Rate limiting storage
request_log = {}

class APIResponse:
    """Standart API response formatı"""
    @staticmethod
    def success(data: Any, message: str = "Success", status_code: int = 200):
        return jsonify({
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }), status_code
    
    @staticmethod
    def error(message: str, error_code: str = "ERROR", status_code: int = 400):
        return jsonify({
            "status": "error",
            "message": message,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat()
        }), status_code

def get_db_connection():
    """Veritabanı bağlantısı al"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        return None

def check_rate_limit(ip: str) -> bool:
    """Rate limiting kontrolü"""
    if not RATE_LIMIT_ENABLED:
        return True
    
    now = datetime.now()
    if ip not in request_log:
        request_log[ip] = []
    
    # Eski istekleri temizle
    request_log[ip] = [t for t in request_log[ip] if (now - t).seconds < RATE_LIMIT_WINDOW]
    
    # Limit kontrolü
    if len(request_log[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    request_log[ip].append(now)
    return True

def rate_limit(f):
    """Rate limit decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_rate_limit(request.remote_addr):
            return APIResponse.error(
                "Rate limit exceeded. Maximum 100 requests per hour.",
                "RATE_LIMIT_EXCEEDED",
                429
            )
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# 📋 HEALTH & INFO ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
@rate_limit
def health_check():
    """Sunucu sağlığı kontrolü"""
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    if conn:
        conn.close()
    
    return APIResponse.success({
        "status": "healthy",
        "database": db_status,
        "version": API_VERSION,
        "analytics_available": ANALYTICS_AVAILABLE,
        "uptime": "running"
    }, "API is healthy")

@app.route('/api/info', methods=['GET'])
@rate_limit
def api_info():
    """API bilgileri ve kullanılabilir endpoints"""
    return APIResponse.success({
        "api_name": "Quran Corpus REST API",
        "version": API_VERSION,
        "description": "Advanced Quran database API with analytics, search, and export features",
        "endpoints": {
            "Health": "/api/health",
            "Verses": "/api/verses/{surah}/{verse}",
            "Search": "/api/search",
            "Analytics": "/api/analytics/*",
            "Morphology": "/api/morphology/*",
            "Export": "/api/export/*"
        },
        "rate_limit": {
            "enabled": RATE_LIMIT_ENABLED,
            "requests_per_hour": RATE_LIMIT_REQUESTS
        }
    })

# ============================================================================
# 📚 VERSES ENDPOINTS
# ============================================================================

@app.route('/api/verses/<int:surah>/<int:verse>', methods=['GET'])
@rate_limit
def get_verse(surah: int, verse: int):
    """Belirli bir ayeti al - tüm meal ve özellikleri"""
    try:
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        
        # Temel ayet verileri
        cursor.execute("""
            SELECT sura, aya, text_simple, text_uthmani
            FROM tanzil_texts
            WHERE sura = ? AND aya = ?
        """, (surah, verse))
        
        verse_data = cursor.fetchone()
        if not verse_data:
            return APIResponse.error(f"Verse {surah}:{verse} not found", "NOT_FOUND", 404)
        
        result = {
            "reference": f"{surah}:{verse}",
            "sura": verse_data['sura'],
            "verse": verse_data['aya'],
            "arabic": {
                "simple": verse_data['text_simple'],
                "uthmani": verse_data['text_uthmani']
            },
            "translations": {},
            "morphology": None
        }
        
        # Çeviriler
        cursor.execute("""
            SELECT translator_id, text
            FROM enhanced_translations
            WHERE sura = ? AND verse = ?
        """, (surah, verse))
        
        for row in cursor.fetchall():
            result['translations'][row['translator_id']] = row['text']
        
        # Diyanet Meali
        cursor.execute("""
            SELECT meal FROM diyanet_meal
            WHERE surah = ? AND verse = ?
        """, (surah, verse))
        
        diyanet = cursor.fetchone()
        if diyanet:
            result['translations']['diyanet'] = diyanet['meal']
        
        # Transliterasyon
        cursor.execute("""
            SELECT transliteration FROM transliteration
            WHERE surah = ? AND verse = ?
        """, (surah, verse))
        
        translit = cursor.fetchone()
        if translit:
            result['transliteration'] = translit['transliteration']
        
        # Morfoloji özeti
        cursor.execute("""
            SELECT COUNT(*) as segment_count
            FROM morphology_segments
            WHERE sura = ? AND verse = ?
        """, (surah, verse))
        
        morph = cursor.fetchone()
        if morph and morph['segment_count'] > 0:
            result['morphology'] = {
                "segments": morph['segment_count'],
                "endpoint": f"/api/morphology/{surah}/{verse}"
            }
        
        conn.close()
        return APIResponse.success(result, f"Verse {surah}:{verse} retrieved successfully")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

@app.route('/api/verses/<int:surah>', methods=['GET'])
@rate_limit
def get_sura(surah: int):
    """Belirli bir surenin tüm ayetlerini al"""
    try:
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        
        # Sure bilgileri
        cursor.execute("""
            SELECT sura_number, sura_name_turkish, verse_count
            FROM sura_info
            WHERE sura_number = ?
        """, (surah,))
        
        sura_info = cursor.fetchone()
        if not sura_info:
            return APIResponse.error(f"Surah {surah} not found", "NOT_FOUND", 404)
        
        # Ayetleri al
        cursor.execute("""
            SELECT sura, aya, text_simple
            FROM tanzil_texts
            WHERE sura = ?
            ORDER BY aya
        """, (surah,))
        
        verses = []
        for row in cursor.fetchall():
            verses.append({
                "verse_number": row['aya'],
                "text": row['text_simple'],
                "reference": f"{row['sura']}:{row['aya']}"
            })
        
        result = {
            "surah": surah,
            "name": sura_info['sura_name_turkish'],
            "verse_count": sura_info['verse_count'],
            "verses": verses
        }
        
        conn.close()
        return APIResponse.success(result, f"Surah {surah} retrieved successfully")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

# ============================================================================
# 🔍 SEARCH ENDPOINTS
# ============================================================================

@app.route('/api/search', methods=['GET'])
@rate_limit
def search():
    """Kapsamlı arama - kelime, kök, morfoloji"""
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'word').lower()  # word, root, lemma
        limit = min(int(request.args.get('limit', 50)), 500)
        
        if not query or len(query) < 2:
            return APIResponse.error("Query must be at least 2 characters", "INVALID_INPUT", 400)
        
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        results = []
        
        if search_type == 'root':
            # Kök bazlı arama
            cursor.execute("""
                SELECT DISTINCT sura, verse, word_arabic, root, lemma
                FROM morphology_segments
                WHERE root LIKE ?
                LIMIT ?
            """, (f"%{query}%", limit))
            
            for row in cursor.fetchall():
                results.append({
                    "reference": f"{row['sura']}:{row['verse']}",
                    "type": "morphology",
                    "word": row['word_arabic'],
                    "root": row['root'],
                    "lemma": row['lemma']
                })
        
        elif search_type == 'lemma':
            # Lemma bazlı arama
            cursor.execute("""
                SELECT DISTINCT sura, verse, segment_arabic, lemma
                FROM morphology_segments
                WHERE lemma LIKE ?
                LIMIT ?
            """, (f"%{query}%", limit))
            
            for row in cursor.fetchall():
                results.append({
                    "reference": f"{row['sura']}:{row['verse']}",
                    "type": "morphology",
                    "segment": row['segment_arabic'],
                    "lemma": row['lemma']
                })
        
        else:  # word search (default)
            # Metin araması
            cursor.execute("""
                SELECT sura, aya, text_simple
                FROM tanzil_texts
                WHERE text_simple LIKE ?
                LIMIT ?
            """, (f"%{query}%", limit))
            
            for row in cursor.fetchall():
                results.append({
                    "reference": f"{row['sura']}:{row['aya']}",
                    "type": "verse",
                    "text": row['text_simple']
                })
        
        conn.close()
        
        return APIResponse.success({
            "query": query,
            "search_type": search_type,
            "result_count": len(results),
            "results": results
        }, f"Found {len(results)} results for '{query}'")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

# ============================================================================
# 📊 ANALYTICS ENDPOINTS
# ============================================================================

@app.route('/api/analytics/statistics', methods=['GET'])
@rate_limit
def analytics_statistics():
    """İstatistiksel analiz sonuçları"""
    if not ANALYTICS_AVAILABLE:
        return APIResponse.error(
            "Analytics not available",
            "FEATURE_NOT_AVAILABLE",
            503
        )
    
    try:
        analytics = AdvancedAnalytics()
        results = analytics.perform_statistical_analysis()
        
        if not results:
            return APIResponse.error("Analytics computation failed", "COMPUTE_ERROR", 500)
        
        return APIResponse.success({
            "analysis_type": "statistical",
            "statistics": results.get('basic_statistics', {}),
            "sura_statistics": results.get('sura_statistics', {}),
            "length_distribution": results.get('length_distribution', {})
        }, "Statistical analysis completed")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

@app.route('/api/analytics/clusters', methods=['GET'])
@rate_limit
def analytics_clusters():
    """Metin kümeleme analizi"""
    if not ANALYTICS_AVAILABLE:
        return APIResponse.error("Analytics not available", "FEATURE_NOT_AVAILABLE", 503)
    
    try:
        algorithm = request.args.get('algorithm', 'kmeans')
        n_clusters = int(request.args.get('clusters', 5))
        
        analytics = AdvancedAnalytics()
        results = analytics.run_text_clustering(algorithm, n_clusters if algorithm == 'kmeans' else None)
        
        if not results:
            return APIResponse.error("Clustering computation failed", "COMPUTE_ERROR", 500)
        
        return APIResponse.success({
            "analysis_type": "clustering",
            "algorithm": results.get('algorithm'),
            "clusters_found": results.get('clusters_found'),
            "quality_metrics": results.get('quality_metrics', {})
        }, "Clustering analysis completed")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

@app.route('/api/analytics/topics', methods=['GET'])
@rate_limit
def analytics_topics():
    """Konu modelleme analizi"""
    if not ANALYTICS_AVAILABLE:
        return APIResponse.error("Analytics not available", "FEATURE_NOT_AVAILABLE", 503)
    
    try:
        algorithm = request.args.get('algorithm', 'lda')
        n_topics = int(request.args.get('topics', 10))
        
        analytics = AdvancedAnalytics()
        results = analytics.run_topic_modeling(algorithm, n_topics)
        
        if not results:
            return APIResponse.error("Topic modeling failed", "COMPUTE_ERROR", 500)
        
        return APIResponse.success({
            "analysis_type": "topic_modeling",
            "algorithm": results.get('algorithm'),
            "topics_found": results.get('topics_found'),
            "model_quality": results.get('model_quality', {})
        }, "Topic modeling completed")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

@app.route('/api/analytics/similarity', methods=['GET'])
@rate_limit
def analytics_similarity():
    """Semantik benzerlik analizi"""
    if not ANALYTICS_AVAILABLE:
        return APIResponse.error("Analytics not available", "FEATURE_NOT_AVAILABLE", 503)
    
    try:
        method = request.args.get('method', 'tfidf')
        threshold = float(request.args.get('threshold', 0.7))
        
        analytics = AdvancedAnalytics()
        results = analytics.run_semantic_similarity(method, threshold)
        
        if not results:
            return APIResponse.error("Similarity analysis failed", "COMPUTE_ERROR", 500)
        
        return APIResponse.success({
            "analysis_type": "semantic_similarity",
            "method": results.get('method'),
            "threshold": results.get('threshold'),
            "similar_pairs_found": results.get('similar_pairs', 0)
        }, "Similarity analysis completed")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

# ============================================================================
# 🔬 MORPHOLOGY ENDPOINTS
# ============================================================================

@app.route('/api/morphology/<int:surah>/<int:verse>', methods=['GET'])
@rate_limit
def get_morphology(surah: int, verse: int):
    """Belirli ayetin morfoloji analizi"""
    try:
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                word_number, segment_arabic, segment_transliteration,
                pos_tag, pos_description, root, lemma, features
            FROM morphology_segments
            WHERE sura = ? AND verse = ?
            ORDER BY word_number
        """, (surah, verse))
        
        segments = []
        for row in cursor.fetchall():
            segments.append({
                "word_number": row['word_number'],
                "segment": row['segment_arabic'],
                "transliteration": row['segment_transliteration'],
                "pos": {
                    "tag": row['pos_tag'],
                    "description": row['pos_description']
                },
                "root": row['root'],
                "lemma": row['lemma'],
                "features": row['features']
            })
        
        if not segments:
            return APIResponse.error(
                f"No morphology data for {surah}:{verse}",
                "NOT_FOUND",
                404
            )
        
        conn.close()
        
        return APIResponse.success({
            "reference": f"{surah}:{verse}",
            "segment_count": len(segments),
            "segments": segments
        }, f"Morphology data for {surah}:{verse} retrieved")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

@app.route('/api/morphology/search', methods=['GET'])
@rate_limit
def search_morphology():
    """Morfoloji özelliklerine göre arama"""
    try:
        pos_tag = request.args.get('pos')
        root = request.args.get('root')
        limit = min(int(request.args.get('limit', 50)), 500)
        
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT sura, verse, segment_arabic, pos_tag, root FROM morphology_segments WHERE 1=1"
        params = []
        
        if pos_tag:
            query += " AND pos_tag = ?"
            params.append(pos_tag)
        
        if root:
            query += " AND root = ?"
            params.append(root)
        
        query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "reference": f"{row['sura']}:{row['verse']}",
                "segment": row['segment_arabic'],
                "pos": row['pos_tag'],
                "root": row['root']
            })
        
        conn.close()
        
        return APIResponse.success({
            "filters": {"pos_tag": pos_tag, "root": root},
            "result_count": len(results),
            "results": results
        }, f"Found {len(results)} morphology results")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

# ============================================================================
# 💾 EXPORT ENDPOINTS
# ============================================================================

@app.route('/api/export/json', methods=['GET'])
@rate_limit
def export_json():
    """Veri JSON formatında dışa aktar"""
    try:
        surah = request.args.get('surah', type=int)
        verse = request.args.get('verse', type=int)
        
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        export_data = []
        
        if surah and verse:
            # Tek ayet
            cursor.execute("""
                SELECT sura, aya, text_simple FROM tanzil_texts
                WHERE sura = ? AND aya = ?
            """, (surah, verse))
            
            row = cursor.fetchone()
            if not row:
                return APIResponse.error(f"Verse {surah}:{verse} not found", "NOT_FOUND", 404)
            
            export_data.append({
                "reference": f"{row['sura']}:{row['aya']}",
                "text": row['text_simple']
            })
        
        elif surah:
            # Tüm sure
            cursor.execute("""
                SELECT sura, aya, text_simple FROM tanzil_texts
                WHERE sura = ? ORDER BY aya
            """, (surah,))
            
            for row in cursor.fetchall():
                export_data.append({
                    "reference": f"{row['sura']}:{row['aya']}",
                    "text": row['text_simple']
                })
        
        conn.close()
        
        return APIResponse.success({
            "format": "json",
            "record_count": len(export_data),
            "data": export_data
        }, "Data exported successfully")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

# ============================================================================
# 📊 STATISTICS ENDPOINTS
# ============================================================================

@app.route('/api/statistics', methods=['GET'])
@rate_limit
def get_statistics():
    """Sistem istatistikleri"""
    try:
        conn = get_db_connection()
        if not conn:
            return APIResponse.error("Database connection failed", "DB_ERROR", 500)
        
        cursor = conn.cursor()
        
        # Toplam ayet sayısı
        cursor.execute("SELECT COUNT(*) as count FROM tanzil_texts")
        total_verses = cursor.fetchone()['count']
        
        # Toplam sure sayısı
        cursor.execute("SELECT COUNT(*) as count FROM sura_info")
        total_suras = cursor.fetchone()['count']
        
        # Toplam çeviri
        cursor.execute("SELECT COUNT(DISTINCT translator_id) as count FROM enhanced_translations")
        total_translations = cursor.fetchone()['count']
        
        # Morfoloji segmentleri
        cursor.execute("SELECT COUNT(*) as count FROM morphology_segments")
        total_segments = cursor.fetchone()['count']
        
        conn.close()
        
        return APIResponse.success({
            "database": {
                "total_verses": total_verses,
                "total_suras": total_suras,
                "total_translations": total_translations,
                "total_morphology_segments": total_segments
            },
            "api": {
                "version": API_VERSION,
                "rate_limit_enabled": RATE_LIMIT_ENABLED,
                "analytics_available": ANALYTICS_AVAILABLE
            }
        }, "Statistics retrieved successfully")
        
    except Exception as e:
        return APIResponse.error(f"Error: {str(e)}", "SERVER_ERROR", 500)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 - Bulunamadı"""
    return APIResponse.error(
        "Endpoint not found",
        "NOT_FOUND",
        404
    )

@app.errorhandler(500)
def server_error(error):
    """500 - Sunucu hatası"""
    return APIResponse.error(
        "Internal server error",
        "SERVER_ERROR",
        500
    )

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("🔌 QURAN CORPUS REST API SERVER")
    print("=" * 70)
    print()
    print(f"📌 API Version: {API_VERSION}")
    print(f"🗄️  Database: {DB_PATH}")
    print(f"⚡ Analytics: {'✅ Available' if ANALYTICS_AVAILABLE else '❌ Not Available'}")
    print(f"🛡️  Rate Limiting: {RATE_LIMIT_REQUESTS} requests/hour")
    print()
    print("📚 API Documentation:")
    print("  • http://localhost:5000/api/info")
    print("  • http://localhost:5000/api/health")
    print()
    
    # Railway için PORT environment variable'ını kullan
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on http://0.0.0.0:{port}")
    print("=" * 70)
    print()
    
    # DEBUG mode test amaçlı false
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )