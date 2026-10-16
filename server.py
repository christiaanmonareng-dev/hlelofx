import os, sqlite3, hmac
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, jsonify, request, session, redirect, url_for, render_template_string, send_from_directory

ROOT=os.path.dirname(os.path.abspath(__file__))
DB_PATH=os.path.join(ROOT,"hlelofx_usage.sqlite3")
app=Flask(__name__,static_folder="static")
app.secret_key=os.environ.get("HLELOFX_SECRET_KEY")
if not app.secret_key:
    # Safe for local testing only. Public deployment must set HLELOFX_SECRET_KEY.
    app.secret_key="local-development-only-change-before-deploy"
OWNER_PASSWORD=os.environ.get("HLELOFX_OWNER_PASSWORD","change-me-now")
OWNER_EMAIL=os.environ.get("HLELOFX_OWNER_EMAIL","hlelomabuza@icloud.com").strip().lower()
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax")

def db():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def now():
 return datetime.now(timezone.utc).isoformat(timespec="seconds")
def init_db():
 with db() as c:
  c.execute("CREATE TABLE IF NOT EXISTS visits(email TEXT PRIMARY KEY, first_seen_utc TEXT NOT NULL, last_seen_utc TEXT NOT NULL, visits INTEGER NOT NULL DEFAULT 1)")
  c.execute("CREATE TABLE IF NOT EXISTS access_events(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL,accessed_utc TEXT NOT NULL)")
def owner_only(fn):
 @wraps(fn)
 def wrapped(*a,**kw):
  if not session.get("owner"): return redirect("/owner")
  return fn(*a,**kw)
 return wrapped

@app.get("/")
def home(): return send_from_directory(app.static_folder,"HleloFX-AI.html")
@app.get("/api/session")
def api_session(): return jsonify(authorized=bool(session.get("visitor_email")))
@app.post("/api/access")
def access():
 data=request.get_json(silent=True) or {}; email=str(data.get("email","")).strip().lower()
 if len(email)>254 or "@" not in email or "." not in email.rsplit("@",1)[-1]:
  return jsonify(ok=False,error="Enter a valid email address."),400
 t=now()
 with db() as c:
  c.execute("INSERT INTO access_events(email,accessed_utc) VALUES(?,?)",(email,t))
  c.execute("""INSERT INTO visits VALUES(?,?,?,1) ON CONFLICT(email) DO UPDATE SET last_seen_utc=excluded.last_seen_utc,visits=visits+1""",(email,t,t))
 session["visitor_email"]=email
 return jsonify(ok=True)

LOGIN="""<!doctype html><html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>HleloFX Owner Login</title><style>body{margin:0;background:#080b12;color:#eef3fb;font:15px system-ui;min-height:100vh;display:grid;place-items:center}.card{width:min(400px,calc(100% - 40px));background:#101622;border:1px solid #253044;border-radius:18px;padding:26px}p{color:#98a6bc;line-height:1.5}input{width:100%;box-sizing:border-box;padding:13px;border-radius:9px;background:#080d16;color:white;border:1px solid #33435a;margin:8px 0 14px}button{width:100%;padding:13px;background:#36e0a1;border:0;border-radius:9px;font-weight:800}.err{color:#ff8290}</style><body><div class=card><h1>HleloFX Owner Portal</h1><p>Sign in to view emails that accessed your website.</p><form method=post action=/owner/login><label>Owner email</label><input type=email name=email value="hlelomabuza@icloud.com" required autocomplete=username><label>Owner password</label><input type=password name=password required autocomplete=current-password autofocus><button>Sign in</button></form><p class=err>{{error}}</p><p style='font-size:11px'>Default password: change-me-now. Change it before public hosting.</p></div></body></html>"""
DASH="""<!doctype html><html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>HleloFX Owner Dashboard</title><style>body{margin:0;background:#080b12;color:#eef3fb;font:14px system-ui;padding:28px}main{max-width:1100px;margin:auto}.top{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}.muted{color:#92a0b5}.stat{display:inline-block;background:#101622;border:1px solid #253044;border-radius:12px;padding:16px;margin:12px 10px 12px 0}table{width:100%;border-collapse:collapse;background:#101622}th,td{text-align:left;padding:13px;border-bottom:1px solid #253044;overflow-wrap:anywhere}th{color:#36e0a1;background:#141c2a}button{padding:9px 12px;background:#182438;color:white;border:1px solid #34425a;border-radius:8px}a{color:#36e0a1}.wrap{overflow-x:auto}</style><body><main><div class=top><div><h1>HleloFX Owner Dashboard</h1><p class=muted>Access log · times shown in UTC</p></div><form method=post action=/owner/logout><button>Log out</button></form></div><div class=stat>Unique emails: <b>{{users|length}}</b></div><div class=stat>Total access events: <b>{{events}}</b></div><h2>Visitors</h2>{% if users %}<div class=wrap><table><tr><th>Email</th><th>First access UTC</th><th>Last access UTC</th><th>Visits</th></tr>{% for u in users %}<tr><td>{{u["email"]}}</td><td>{{u["first_seen_utc"]}}</td><td>{{u["last_seen_utc"]}}</td><td>{{u["visits"]}}</td></tr>{% endfor %}</table></div>{% else %}<p class=muted>No emails recorded yet.</p>{% endif %}<p class=muted style='font-size:11px'>Use email data transparently, secure the owner password, and delete records when no longer needed.</p><a href=/>← Back to HleloFX</a></main></body></html>"""

@app.get("/owner")
def owner_login():
 if session.get("owner"): return redirect("/owner/dashboard")
 return render_template_string(LOGIN,error="")
@app.post("/owner/login")
def owner_login_post():
 if hmac.compare_digest(request.form.get("email","").strip().lower(),OWNER_EMAIL) and hmac.compare_digest(request.form.get("password",""),OWNER_PASSWORD):
  session["owner"]=True; return redirect("/owner/dashboard")
 return render_template_string(LOGIN,error="Incorrect password.")
@app.post("/owner/logout")
def logout():
 session.clear(); return redirect("/owner")
@app.get("/owner/dashboard")
@owner_only
def dashboard():
 with db() as c:
  users=c.execute("SELECT * FROM visits ORDER BY last_seen_utc DESC").fetchall()
  events=c.execute("SELECT COUNT(*) n FROM access_events").fetchone()["n"]
 return render_template_string(DASH,users=users,events=events)

# Initialize tables when the app is imported by a production WSGI server.
init_db()

if __name__=="__main__":
 print("HleloFX: http://127.0.0.1:8000")
 print("Owner portal: http://127.0.0.1:8000/owner")
 print("OWNER EMAIL: " + OWNER_EMAIL)
 print("DEFAULT OWNER PASSWORD: change-me-now")
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT","8000")),debug=False)
