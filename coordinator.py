import json, os, sqlite3, threading, time, uuid
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request
import requests

app=Flask(__name__)
DB=os.environ.get('TASKGRID_DB',os.path.join(os.path.dirname(__file__),'taskgrid.db'))
mutex=threading.RLock(); workers={}; MAX_ATTEMPTS=3; HEARTBEAT_TIMEOUT=7; LEASE=25

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def conn():
    db=sqlite3.connect(DB,timeout=10);db.row_factory=sqlite3.Row;return db

def init_db():
    with conn() as db:
        db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, type TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, worker TEXT, attempt INTEGER DEFAULT 0, created TEXT NOT NULL, updated TEXT NOT NULL, result TEXT, error TEXT, assigned_at REAL)')
        db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, message TEXT, created TEXT)')
        db.execute("UPDATE tasks SET state='queued',worker=NULL,assigned_at=NULL WHERE state='running'")

def event(db,task_id,message): db.execute('INSERT INTO events(task_id,message,created) VALUES(?,?,?)',(task_id,message,now()))

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/state')
def state():
    with mutex:
        with conn() as db:
            tasks=[dict(r) for r in db.execute('SELECT * FROM tasks ORDER BY created DESC LIMIT 120')]
            events=[dict(r) for r in db.execute('SELECT * FROM events ORDER BY id DESC LIMIT 35')]
        for t in tasks:
            t['payload']=json.loads(t['payload']);t['result']=json.loads(t['result']) if t['result'] else None
        current=time.monotonic()
        nodes=[dict(v,online=current-v['last_seen']<HEARTBEAT_TIMEOUT) for v in workers.values()]
        for n in nodes: n.pop('last_seen',None)
        return jsonify(tasks=tasks,events=events,workers=nodes)

@app.post('/api/tasks')
def submit():
    body=request.get_json(silent=True) or {}; kind=body.get('type');payload=body.get('payload',{})
    if kind not in ('prime','fibonacci','statistics','wordcount','benchmark') or not isinstance(payload,dict): return jsonify(error='Invalid task type or payload'),400
    tid=str(uuid.uuid4())[:8]
    with mutex:
        with conn() as db:
            db.execute('INSERT INTO tasks(id,type,payload,state,created,updated) VALUES(?,?,?,?,?,?)',(tid,kind,json.dumps(payload),'queued',now(),now()))
            event(db,tid,'Task added to queue')
    return jsonify(id=tid,state='queued'),201

@app.post('/api/heartbeat')
def heartbeat():
    b=request.get_json(silent=True) or {};wid=b.get('id');url=b.get('url','')
    if not isinstance(wid,str) or not wid.startswith('worker-') or url not in [f'http://127.0.0.1:{p}' for p in range(5001,5011)]:return jsonify(error='Invalid worker'),400
    with mutex: workers[wid]={'id':wid,'url':url,'load':max(0,int(b.get('load',0))),'capacity':max(1,min(16,int(b.get('capacity',2)))),'last_seen':time.monotonic()}
    return jsonify(ok=True)

@app.post('/api/result')
def result():
    b=request.get_json(silent=True) or {};tid=b.get('id');attempt=b.get('attempt');wid=b.get('worker')
    with mutex:
        with conn() as db:
            row=db.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
            if not row or row['state']!='running' or row['attempt']!=attempt or row['worker']!=wid:return jsonify(accepted=False,reason='Stale result'),409
            status='completed' if b.get('state')=='completed' else 'failed'
            db.execute('UPDATE tasks SET state=?,result=?,error=?,updated=?,assigned_at=NULL WHERE id=?',(status,json.dumps(b.get('result')) if status=='completed' else None,b.get('error'),now(),tid))
            event(db,tid,f'{status.capitalize()} by {wid}')
    return jsonify(accepted=True)

@app.post('/api/tasks/<tid>/retry')
def retry(tid):
    with mutex:
        with conn() as db:
            row=db.execute('SELECT state FROM tasks WHERE id=?',(tid,)).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['state'] not in ('failed','completed'):return jsonify(error='Only finished tasks can be retried'),409
            db.execute("UPDATE tasks SET state='queued',worker=NULL,attempt=0,result=NULL,error=NULL,updated=?,assigned_at=NULL WHERE id=?",(now(),tid));event(db,tid,'Manually queued for retry')
    return jsonify(ok=True)

def scheduler():
    while True:
        try: schedule_once()
        except Exception as exc: print('Scheduler warning:',exc,flush=True)
        time.sleep(1)

def schedule_once():
    with mutex:
        clock=time.monotonic()
        with conn() as db:
            running=db.execute("SELECT * FROM tasks WHERE state='running'").fetchall()
            for t in running:
                node=workers.get(t['worker']); offline=not node or clock-node['last_seen']>HEARTBEAT_TIMEOUT
                expired=t['assigned_at'] is not None and time.time()-t['assigned_at']>LEASE
                if offline or expired:
                    next_state='failed' if t['attempt']>=MAX_ATTEMPTS else 'queued'
                    db.execute('UPDATE tasks SET state=?,worker=NULL,updated=?,assigned_at=NULL,error=? WHERE id=?',(next_state,now(),'Maximum attempts reached' if next_state=='failed' else None,t['id']))
                    event(db,t['id'],f"Worker timeout; task {next_state} (attempt {t['attempt']})")
            queued=db.execute("SELECT * FROM tasks WHERE state='queued' ORDER BY created ASC LIMIT 20").fetchall()
            online=[w for w in workers.values() if clock-w['last_seen']<HEARTBEAT_TIMEOUT]
            loads={w['id']:max(w['load'],db.execute("SELECT COUNT(*) FROM tasks WHERE state='running' AND worker=?",(w['id'],)).fetchone()[0]) for w in online}
            for task in queued:
                available=[w for w in online if loads[w['id']]<w['capacity']]
                if not available:break
                worker=min(available,key=lambda w:(loads[w['id']]/w['capacity'],loads[w['id']],w['id']))
                attempt=task['attempt']+1
                try:
                    resp=requests.post(worker['url']+'/execute',json={'id':task['id'],'attempt':attempt,'type':task['type'],'payload':json.loads(task['payload'])},timeout=1.5)
                    if resp.status_code!=202:continue
                except requests.RequestException:continue
                db.execute("UPDATE tasks SET state='running',worker=?,attempt=?,updated=?,assigned_at=? WHERE id=?",(worker['id'],attempt,now(),time.time(),task['id']))
                event(db,task['id'],f"Assigned to {worker['id']} (attempt {attempt})")
                loads[worker['id']]+=1

if __name__=='__main__':
    init_db();threading.Thread(target=scheduler,daemon=True).start()
    app.run(host='127.0.0.1',port=5000,threaded=True,use_reloader=False)
