import argparse, os, threading, time
import requests
from flask import Flask, jsonify, request
from core import compute

app=Flask(__name__)
config={'id':'worker-1','port':5001,'coordinator':'http://127.0.0.1:5000','capacity':2}
lock=threading.Lock(); active=set()

def heartbeat_loop():
    while True:
        with lock: load=len(active)
        try: requests.post(config['coordinator']+'/api/heartbeat',json={'id':config['id'],'url':f"http://127.0.0.1:{config['port']}",'load':load,'capacity':config['capacity']},timeout=2)
        except requests.RequestException: pass
        time.sleep(2)

def execute(task):
    tid=task['id']; attempt=task['attempt']
    try:
        result=compute(task['type'],task['payload']); state='completed'; error=None
    except Exception as exc:
        result=None; state='failed'; error=str(exc)
    with lock: active.discard(tid)
    try: requests.post(config['coordinator']+'/api/result',json={'id':tid,'attempt':attempt,'worker':config['id'],'state':state,'result':result,'error':error},timeout=5)
    except requests.RequestException: pass

@app.post('/execute')
def accept():
    task=request.get_json(silent=True) or {}
    with lock:
        if len(active)>=config['capacity']: return jsonify(error='Worker busy'),429
        if task.get('id') in active: return jsonify(error='Duplicate task'),409
        active.add(task['id'])
    threading.Thread(target=execute,args=(task,),daemon=True).start()
    return jsonify(accepted=True),202

@app.get('/health')
def health():
    with lock: count=len(active)
    return jsonify(id=config['id'],load=count,capacity=config['capacity'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--id',default='worker-1');parser.add_argument('--port',type=int,default=5001);parser.add_argument('--coordinator',default='http://127.0.0.1:5000');parser.add_argument('--capacity',type=int,default=2)
    config.update(vars(parser.parse_args()))
    threading.Thread(target=heartbeat_loop,daemon=True).start()
    app.run(host='127.0.0.1',port=config['port'],threaded=True,use_reloader=False)
