import random
import copy
import json
import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

DEEPSEEK_API_KEY = "sk-f6b3102959a34c10bb24cbe98402368c"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class SmallAI:
    def __init__(self, name, system_prompt, temperature=0.7):
        self.name = name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.fitness = 0

    def generate(self, user_input, history):
        messages = [{"role": "system", "content": self.system_prompt}]
        for h in history[-10:]:
            messages.append({"role": "user", "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_input})

        try:
            resp = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": 200
                },
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            return "抱歉，API出了点问题。"
        except Exception as e:
            print(f"API错误: {e}")
            return "嗯，能再说说吗？"

    def copy(self):
        return copy.deepcopy(self)

    def mutate(self):
        if random.random() < 0.3:
            self.temperature += random.uniform(-0.2, 0.2)
            self.temperature = max(0.2, min(1.2, self.temperature))

    def to_dict(self):
        return {
            'name': self.name,
            'system_prompt': self.system_prompt,
            'temperature': self.temperature,
            'fitness': self.fitness
        }

    @staticmethod
    def from_dict(d):
        ai = SmallAI(d['name'], d['system_prompt'], d['temperature'])
        ai.fitness = d.get('fitness', 0)
        return ai


def create_ais():
    return [
        SmallAI("温柔型", "你是一个温柔、有耐心的朋友。说话自然，认真回答用户的问题。", 0.6),
        SmallAI("幽默型", "你是一个幽默风趣的人。喜欢开玩笑，但也要认真回答用户的问题。", 0.9),
        SmallAI("理性型", "你是一个理性、逻辑清晰的思考者。直接回答用户的问题，有条理。", 0.5),
        SmallAI("热情型", "你是一个热情的朋友。充满活力，认真回答每个问题。", 0.8)
    ]


class ChatAI:
    def __init__(self, save_file='memory.json'):
        self.save_file = save_file
        self.ais = []
        self.history = []
        self.total = 0
        self.last_ai = None
        if os.path.exists(save_file):
            self.load()
        else:
            self.ais = create_ais()

    def select_best(self):
        return max(self.ais, key=lambda a: a.fitness)

    def evolve(self, ai, feedback):
        if feedback > 0:
            ai.fitness += 10
        else:
            ai.fitness -= 20
        ai.fitness = max(-100, min(500, ai.fitness))
        self.ais.sort(key=lambda a: a.fitness, reverse=True)
        self.ais = self.ais[:3]
        while len(self.ais) < 4:
            child = self.ais[0].copy()
            child.mutate()
            child.fitness = self.ais[0].fitness - 5
            self.ais.append(child)

    def respond(self, msg, feedback=0):
        self.total += 1
        if feedback != 0 and self.last_ai:
            self.evolve(self.last_ai, feedback)
        best = self.select_best()
        reply = best.generate(msg, self.history)
        self.history.append({"role": "user", "content": msg})
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 30:
            self.history = self.history[-30:]
        self.last_ai = best
        self.save()
        return reply, best.name

    def save(self):
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total': self.total,
                'history': self.history[-30:],
                'ais': [a.to_dict() for a in self.ais]
            }, f, ensure_ascii=False, indent=2)

    def load(self):
        with open(self.save_file, 'r', encoding='utf-8') as f:
            d = json.load(f)
            self.total = d.get('total', 0)
            self.history = d.get('history', [])
            self.ais = [SmallAI.from_dict(a) for a in d.get('ais', [])]
            if not self.ais:
                self.ais = create_ais()

    def stats(self):
        return {
            'interactions': self.total,
            'current_ais': [{'name': a.name, 'fitness': a.fitness} for a in self.ais]
        }


ai = ChatAI()

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>第3集聊天AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .chat { width: 100%; max-width: 600px; background: white; border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; height: 80vh; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
        .header h1 { font-size: 1.5rem; }
        .messages { flex: 1; overflow-y: auto; padding: 20px; background: #f5f5f5; }
        .msg { margin-bottom: 15px; display: flex; flex-direction: column; }
        .msg.user { align-items: flex-end; }
        .msg.ai { align-items: flex-start; }
        .bubble { max-width: 80%; padding: 10px 15px; border-radius: 18px; word-wrap: break-word; }
        .user .bubble { background: #667eea; color: white; border-bottom-right-radius: 4px; }
        .ai .bubble { background: white; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .name { font-size: 0.7rem; color: #999; margin-bottom: 4px; }
        .feedback { display: flex; gap: 10px; margin-top: 5px; margin-left: 8px; }
        .fb { background: none; border: none; font-size: 1.2rem; cursor: pointer; opacity: 0.5; }
        .fb:hover { opacity: 1; }
        .input-area { display: flex; padding: 20px; background: white; border-top: 1px solid #eee; }
        .input-area input { flex: 1; padding: 12px 16px; border: 1px solid #ddd; border-radius: 25px; font-size: 1rem; outline: none; }
        .input-area button { margin-left: 10px; padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 25px; cursor: pointer; }
        .stats { padding: 8px 20px; background: #f0f0f0; font-size: 0.7rem; text-align: center; color: #666; }
        .typing { color: #999; font-style: italic; }
    </style>
</head>
<body>
<div class="chat">
    <div class="header"><h1>🤖 第3集聊天AI</h1><p>点赞👍点踩👎让AI学习你的偏好</p></div>
    <div class="messages" id="msgs"><div class="msg ai"><span class="name">AI</span><div class="bubble">你好！我是会进化的AI。想问什么直接说～</div></div></div>
    <div class="input-area"><input id="input" placeholder="输入..." onkeypress="if(event.keyCode===13)send()"><button onclick="send()">发送</button></div>
    <div class="stats" id="stats">加载中...</div>
</div>
<script>
async function loadStats(){
    try{
        let r=await fetch('/stats');
        let d=await r.json();
        document.getElementById('stats').innerHTML=`📊 对话${d.interactions}次 | ${d.current_ais.map(a=>a.name).join(', ')}`;
    }catch(e){}
}
async function send(){
    let input=document.getElementById('input');
    let msg=input.value.trim();
    if(!msg)return;
    addMsg(msg,'user');
    input.value='';
    let typing=addTyping();
    try{
        let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,feedback:0})});
        let d=await r.json();
        typing.remove();
        let id=addMsg(d.response,'ai',d.ai_name);
        addFB(id,d.ai_name);
        loadStats();
    }catch(e){typing.remove();addMsg('出错了','ai','Error');}
}
async function sendFB(id,name,fb){
    let el=document.getElementById(`msg-${id}`);
    if(!el)return;
    el.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));
    if(fb===1)el.querySelector('.fb-up')?.classList.add('active');
    if(fb===-1)el.querySelector('.fb-down')?.classList.add('active');
    await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ai_name:name,feedback:fb})});
}
function addMsg(text,sender,name=null){
    let div=document.getElementById('msgs');
    let id=Date.now()+Math.random();
    let m=document.createElement('div');
    m.className=`msg ${sender}`;
    m.id=`msg-${id}`;
    m.innerHTML=`<span class="name">${sender==='user'?'你':(name||'AI')}</span><div class="bubble">${escapeHtml(text)}</div>`;
    div.appendChild(m);
    div.scrollTop=div.scrollHeight;
    return id;
}
function addFB(id,name){
    let el=document.getElementById(`msg-${id}`);
    if(!el)return;
    let d=document.createElement('div');
    d.className='feedback';
    d.innerHTML=`<button class="fb fb-up" onclick="sendFB('${id}','${name}',1)">👍</button><button class="fb fb-down" onclick="sendFB('${id}','${name}',-1)">👎</button>`;
    el.appendChild(d);
}
function addTyping(){
    let div=document.getElementById('msgs');
    let t=document.createElement('div');
    t.className='msg ai';
    t.innerHTML='<span class="name">AI</span><div class="bubble typing">思考中...</div>';
    div.appendChild(t);
    div.scrollTop=div.scrollHeight;
    return t;
}
function escapeHtml(t){let d=document.createElement('div');d.textContent=t;return d.innerHTML;}
loadStats();
setInterval(loadStats,30000);
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    msg = data.get('message', '')
    fb = data.get('feedback', 0)
    if not msg:
        return jsonify({'error': 'empty'}), 400
    reply, name = ai.respond(msg, fb)
    return jsonify({'response': reply, 'ai_name': name})

@app.route('/feedback', methods=['POST'])
def feedback():
    return jsonify({'status': 'ok'})

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify(ai.stats())

if __name__ == '__main__':
    print("="*50)
    print("🚀 启动成功！打开浏览器访问 http://localhost:5000")
    print("="*50)
    app.run(host='0.0.0.0', port=5000, debug=False)
