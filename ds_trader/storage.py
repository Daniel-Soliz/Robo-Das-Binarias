"""SQLite local e exportação completa; sem credenciais nem serviços externos."""
import csv
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class Store:
    def __init__(self,path=None):
        base=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'DS Trader'
        self.path=Path(path) if path else base/'history.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path)
        self.db.executescript('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, body TEXT NOT NULL); CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, created TEXT NOT NULL, body TEXT NOT NULL);')
    def config(self):
        row=self.db.execute('SELECT body FROM settings WHERE id=1').fetchone()
        return json.loads(row[0]) if row else {}
    def save_config(self,body):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (1,?)',(json.dumps(body,ensure_ascii=False),))
    def save(self,report,run_id=None):
        with self.db:
            if run_id is None:
                return self.db.execute('INSERT INTO runs(created,body) VALUES (?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps(report,ensure_ascii=False))).lastrowid
            self.db.execute('UPDATE runs SET body=? WHERE id=?',(json.dumps(report,ensure_ascii=False),run_id))
            return run_id
    def runs(self):
        return self.db.execute('SELECT id,created FROM runs ORDER BY id DESC').fetchall()
    def get(self,run_id):
        return json.loads(self.db.execute('SELECT body FROM runs WHERE id=?',(run_id,)).fetchone()[0])
    def backup(self,target):
        if Path(target).resolve()==self.path.resolve():
            raise ValueError('Escolha outro arquivo para backup')
        with sqlite3.connect(target) as out:
            self.db.backup(out)
    def close(self):
        self.db.close()

def safe_cell(v):
    # Evita fórmulas ao abrir CSV em Excel. O JSON preserva o texto original.
    return "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v

def export_report(report,path):
    path=Path(path)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for kind in ('trades','events'):
        rows=report[kind]
        columns=list(dict.fromkeys(k for r in rows for k in r)) or ['status']
        with path.with_name(path.stem+'_'+kind+'.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,columns); w.writeheader()
            w.writerows({k:safe_cell(v) for k,v in r.items()} for r in rows)
