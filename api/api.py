import aiohttp
from aiohttp import web
import sqlite3
import json
import random
import logging
import socket

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 獲取本機 IP 函數 ---
def get_local_ip():
    try:
        # 創建一個臨時 socket 連接到外部主機（不實際發送數據）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # 使用 Google DNS 作為目標
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"無法獲取本機 IP: {str(e)}")
        return "127.0.0.1"  # 失敗時回退到 localhost

# --- 資料庫相關函數 ---
def get_db_connection():
    conn = sqlite3.connect('./db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS identifier_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warn_id TEXT UNIQUE,
        data TEXT,
        warning_reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    logger.info('✅ 數據表已就緒')

def group_identifiers(identifiers):
    grouped = {
        'steam': [], 'license': [], 'discord': [], 'xbl': [], 'live': [], 'fivem': [], 'ip': []
    }
    for id in identifiers:
        parts = id.split(':', 1)
        if len(parts) == 2:
            type, value = parts
            if type in grouped:
                grouped[type].append(f"{type}:{value}")
    return grouped

def generate_warn_id():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(8))

def generate_unique_warn_id():
    conn = get_db_connection()
    while True:
        warn_id = generate_warn_id()
        result = conn.execute('SELECT 1 FROM identifier_data WHERE warn_id = ?', (warn_id,)).fetchone()
        if not result:
            conn.close()
            return warn_id

# --- API 路由 ---
async def add_identifiers(request):
    try:
        data = await request.json()
        identifiers = data.get('identifiers', [])  # Default to empty list if not provided
        warning_reason = data.get('warning_reason')
        
        # Make warning_reason mandatory
        if not warning_reason or not isinstance(warning_reason, str) or warning_reason.strip() == '':
            return web.json_response({'error': '警告原因為必填欄位'}, status=400)
            
        warn_id = generate_unique_warn_id()
        grouped = group_identifiers(identifiers)
        data_json = json.dumps(grouped)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO identifier_data (warn_id, data, warning_reason) VALUES (?, ?, ?)',
            (warn_id, data_json, warning_reason)
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return web.json_response({
            'success': True,
            'id': last_id,
            'warn_id': warn_id,
            'data': grouped,
            'warning_reason': warning_reason
        }, status=201)
    except json.JSONDecodeError:
        return web.json_response({'error': '無效的JSON格式'}, status=400)
    except Exception as e:
        logger.error(f'伺服器錯誤: {str(e)}')
        return web.json_response({'error': '伺服器內部錯誤'}, status=500)

async def search_warns(request):
    try:
        keyword = request.query.get('keyword', '').strip()
        if not keyword or len(keyword) < 2:
            return web.json_response({'error': '請提供至少2個字符的搜索關鍵詞'}, status=400)
        like_keyword = f"%{keyword}%"
        query = '''
            SELECT * FROM identifier_data
            WHERE warn_id LIKE ?
               OR data LIKE ?
               OR warning_reason LIKE ?
            ORDER BY created_at DESC
        '''
        conn = get_db_connection()
        rows = conn.execute(query, (like_keyword, like_keyword, like_keyword)).fetchall()
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'warn_id': row['warn_id'],
                'warning_reason': row['warning_reason'],
                'created_at': row['created_at'],
                'data': json.loads(row['data'])
            })
        conn.close()
        return web.json_response({'success': True, 'count': len(result), 'result': result})
    except Exception as e:
        logger.error(f'搜索錯誤: {str(e)}')
        return web.json_response({'error': '搜索過程中發生錯誤'}, status=500)

async def delete_warn(request):
    try:
        warn_id = request.match_info['warn_id']
        if not warn_id or len(warn_id) < 1:
            return web.json_response({'error': 'warn_id 不能為空'}, status=400)
        conn = get_db_connection()
        cursor = conn.cursor()
        existing = conn.execute('SELECT 1 FROM identifier_data WHERE warn_id = ?', (warn_id,)).fetchone()
        if not existing:
            conn.close()
            return web.json_response({'error': f'找不到 warn_id 為 {warn_id} 的記錄'}, status=404)
        cursor.execute('DELETE FROM identifier_data WHERE warn_id = ?', (warn_id,))
        conn.commit()
        result = {'success': True, 'message': f'成功刪除 warn_id 為 {warn_id} 的記錄'} if cursor.rowcount > 0 else {'success': False, 'message': '刪除操作未影響任何記錄'}
        conn.close()
        return web.json_response(result)
    except Exception as e:
        logger.error(f'刪除錯誤: {str(e)}')
        return web.json_response({'error': f'刪除過程中發生錯誤: {str(e)}'}, status=500)

# --- API 啟動函數 ---
async def start_api():
    initialize_database()
    app = web.Application()
    app.router.add_post('/add-identifiers', add_identifiers)
    app.router.add_get('/search-warns', search_warns)
    app.router.add_delete('/delete-warn/{warn_id}', delete_warn)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # 動態獲取本機 IP
    host = get_local_ip()
    port = 3000
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"✅ API 伺服器運行於 http://{host}:{port}")
    return runner