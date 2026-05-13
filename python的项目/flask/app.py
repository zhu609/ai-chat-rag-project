import time
import threading
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # 实际使用时请更换

# ---------- 内存存储 ----------
users = {}          # {username: {'password': pwd, 'registered_at': timestamp}}
messages = []       # [{'id': int, 'user': str, 'text': str, 'time': str}]
message_id_counter = 0
lock = threading.Lock()  # 保证多线程安全（开发服务器多线程）

# ---------- 辅助函数 ----------
def get_next_message_id():
    global message_id_counter
    with lock:
        message_id_counter += 1
        return message_id_counter

def add_message(username, text):
    """添加消息到全局列表，并自动限制最大条数（保留最近100条）"""
    with lock:
        msg = {
            'id': get_next_message_id(),
            'user': username,
            'text': text,
            'time': datetime.now().strftime('%H:%M:%S')
        }
        messages.append(msg)
        # 防止消息过多占用内存，保留最近100条
        if len(messages) > 100:
            messages.pop(0)

def get_messages_since(last_id):
    """返回所有 id > last_id 的消息"""
    with lock:
        return [msg for msg in messages if msg['id'] > last_id]

# ---------- 路由 ----------
@app.route('/')
def index():
    """聊天室主页（需要登录）"""
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('register.html', error='用户名和密码不能为空')
        if username in users:
            return render_template('register.html', error='用户名已存在')
        # 保存用户（密码明文存储，演示用，实际应哈希）
        users[username] = {
            'password': password,
            'registered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # 注册后自动登录
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    """我的个人页面（需要登录）"""
    if 'username' not in session:
        return redirect(url_for('login'))
    user_info = users.get(session['username'], {})
    return render_template('profile.html', user=session['username'], info=user_info)

@app.route('/user/<username>')
def user_profile(username):
    """动态路由：查看任意用户的资料页"""
    if username not in users:
        abort(404)
    user_info = users[username]
    return render_template('user.html', username=username, info=user_info)

@app.route('/send', methods=['POST'])
def send_message():
    """发送消息接口"""
    if 'username' not in session:
        return jsonify({'error': '未登录'}), 401
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': '消息不能为空'}), 400
    # 限制消息长度
    if len(text) > 500:
        return jsonify({'error': '消息过长'}), 400
    add_message(session['username'], text)
    return jsonify({'status': 'ok'})

@app.route('/messages')
def get_messages():
    """获取新消息接口（轮询）"""
    last_id = request.args.get('last_id', type=int, default=0)
    new_msgs = get_messages_since(last_id)
    return jsonify(new_msgs)

# ---------- 启动 ----------
if __name__ == '__main__':
    # 添加一条欢迎消息（可选）
    add_message('系统', '✨ 欢迎来到聊天室！注册/登录后即可发言。')
    app.run(debug=True)