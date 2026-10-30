import os
import sys
from flask import Flask, send_file

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = Flask(__name__)

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'index.html'))

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 DASHBOARD ARBITRASE POLYGON 24 KOLAM - MIN CUAN RP 350")
    print("👉 Akses Lokal: http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
