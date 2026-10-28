import json, os, uuid, time, boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]
TYPES = ("certificate", "lab-booking", "fee-receipt")
TTL_DAYS = 30

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QueueFair | Campus Request Portal</title>
<style>
:root{
  --brand:#5b5bd6; --brand-2:#8b5cf6; --bg:#f4f5fb; --card:#ffffff;
  --text:#1c1d2b; --muted:#6b7090; --ok:#16a34a; --warn:#f59e0b;
  --bad:#dc2626; --line:#e4e6f2; --radius:16px;
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text)}
.hide{display:none !important}
header{background:linear-gradient(135deg,var(--brand),var(--brand-2));color:#fff;padding:38px 20px 90px;text-align:center}
header h1{margin:0 0 6px;font-size:30px;letter-spacing:-.5px}
header p{margin:0;opacity:.92}
.who{margin-top:14px;font-size:14px;opacity:.95}
.who a{color:#fff;margin-left:10px;text-decoration:underline;cursor:pointer}
main{max-width:720px;margin:-56px auto 40px;padding:0 16px;display:grid;gap:16px}
.stack{display:grid;gap:16px}
.card{background:var(--card);border-radius:var(--radius);padding:22px;box-shadow:0 8px 24px rgba(40,40,90,.08)}
h2{margin:0 0 12px;font-size:18px}
.muted{color:var(--muted);font-size:14px}
.types{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}
.type{border:2px solid var(--line);border-radius:12px;padding:14px 6px;text-align:center;cursor:pointer;font-size:14px;user-select:none}
.type .ico{font-size:28px;display:block;margin-bottom:4px}
.type.sel{border-color:var(--brand);background:#f0efff;font-weight:600}
.check{display:flex;align-items:center;gap:8px;margin:16px 0 2px;font-size:14px}
button{width:100%;margin-top:14px;padding:14px;border:0;border-radius:12px;background:linear-gradient(135deg,var(--brand),var(--brand-2));color:#fff;font-size:16px;font-weight:600;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}
.err{color:var(--bad);font-size:14px;min-height:18px;margin-top:8px}
.top{display:flex;justify-content:space-between;align-items:center;gap:10px}
.rid{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:var(--muted);word-break:break-all}
.badge{padding:5px 12px;border-radius:99px;font-size:12px;font-weight:700;color:#fff;background:var(--muted)}
.badge.PENDING{background:var(--warn)} .badge.PROCESSING{background:var(--brand)}
.badge.DONE{background:var(--ok)} .badge.FAILED{background:var(--bad)}
.steps{display:flex;margin:20px 0 10px}
.step{flex:1;text-align:center;font-size:13px;color:var(--muted)}
.dot{width:30px;height:30px;border-radius:50%;background:var(--line);margin:0 auto 6px;display:grid;place-items:center;color:#fff;font-weight:700}
.step.on .dot{background:var(--brand);box-shadow:0 0 0 6px #e3e2ff}
.step.done .dot{background:var(--ok)}
.step.done,.step.on{color:var(--text);font-weight:600}
#msg{font-size:15px;margin:6px 0 0}
.live{display:grid;grid-template-columns:1fr 1fr;gap:12px;text-align:center}
.num{font-size:34px;font-weight:800;color:var(--brand);line-height:1.1}
.lbl{font-size:13px;color:var(--muted)}
.track{height:8px;background:var(--line);border-radius:99px;margin-top:16px;overflow:hidden}
#bar{height:100%;width:0;background:linear-gradient(90deg,var(--brand),var(--brand-2));transition:width .6s}
.mrow{display:flex;justify-content:space-between;align-items:center;padding:10px 4px;border-bottom:1px solid var(--line);cursor:pointer;font-size:15px}
.mrow:last-child{border-bottom:0}
footer{text-align:center;color:var(--muted);font-size:12px;padding-bottom:30px}
</style></head><body>
<header>
  <h1>Campus Request Portal</h1>
  <p>Sign in with your college email. Submit once. We queue it, process it and keep you updated.</p>
  <div class="who hide" id="who"><span id="me"></span><a onclick="logout()">Sign out</a></div>
</header>
<main>
  <section class="card" id="login">
    <h2>Welcome</h2>
    <p class="muted">Only students with an approved college email can use this portal. You will get a verification code by email the first time.</p>
    <div class="err" id="autherr"></div>
    <button onclick="login()">Sign in or create account</button>
  </section>

  <div id="app" class="stack hide">
    <section class="card">
      <h2>New request</h2>
      <div class="muted">What do you need?</div>
      <div class="types">
        <div class="type sel" data-type="certificate"><span class="ico">&#127891;</span>Certificate</div>
        <div class="type" data-type="lab-booking"><span class="ico">&#129514;</span>Lab booking</div>
        <div class="type" data-type="fee-receipt"><span class="ico">&#129534;</span>Fee receipt</div>
      </div>
      <label class="check"><input type="checkbox" id="notify" checked> Email me at <b id="mail"></b> when it is done</label>
      <button id="go" onclick="send()">Submit request</button>
      <div class="err" id="err"></div>
    </section>

    <section class="card hide" id="result">
      <div class="top"><h2 style="margin:0">Your request</h2><span class="badge" id="badge">-</span></div>
      <div class="rid">ID: <span id="rid"></span></div>
      <div class="steps">
        <div class="step" id="s1"><div class="dot">1</div>In queue</div>
        <div class="step" id="s2"><div class="dot">2</div>Processing</div>
        <div class="step" id="s3"><div class="dot">3</div>Done</div>
      </div>
      <p id="msg"></p>
    </section>

    <section class="card">
      <h2>Live system status</h2>
      <div class="live">
        <div><div class="num" id="wait">-</div><div class="lbl">Waiting in line</div></div>
        <div><div class="num" id="busy">-</div><div class="lbl">Being processed</div></div>
      </div>
      <div class="track"><div id="bar"></div></div>
    </section>

    <section class="card">
      <h2>My requests</h2>
      <div id="mine" class="muted">Loading...</div>
    </section>
  </div>
</main>
<footer>Built with AWS Cognito, API Gateway, Lambda, SQS, DynamoDB and SES</footer>
<script>
const CFG = {domain: '__COGNITO_DOMAIN__', clientId: '__CLIENT_ID__', redirect: '__REDIRECT_URI__'};
const LABEL = {'certificate': 'Certificate', 'lab-booking': 'Lab booking', 'fee-receipt': 'Fee receipt'};
const $ = id => document.getElementById(id);
let token = null, type = 'certificate', timer = null;

function b64url(buf) {
  return btoa(String.fromCharCode.apply(null, new Uint8Array(buf)))
    .split('+').join('-').split('/').join('_').split('=').join('');
}

function claims(t) {
  try {
    let b = t.split('.')[1].split('-').join('+').split('_').join('/');
    while (b.length % 4) b += '=';
    const bytes = Uint8Array.from(atob(b), c => c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch (e) { return {}; }
}

async function login() {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  sessionStorage.setItem('qf_verifier', verifier);
  const challenge = b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
  location.href = 'https://' + CFG.domain + '/oauth2/authorize?response_type=code'
    + '&client_id=' + CFG.clientId
    + '&redirect_uri=' + encodeURIComponent(CFG.redirect)
    + '&scope=' + encodeURIComponent('openid email profile')
    + '&code_challenge_method=S256&code_challenge=' + challenge;
}

async function finishLogin(code) {
  const body = new URLSearchParams({
    grant_type: 'authorization_code', client_id: CFG.clientId, code: code,
    redirect_uri: CFG.redirect, code_verifier: sessionStorage.getItem('qf_verifier') || ''
  });
  try {
    const r = await fetch('https://' + CFG.domain + '/oauth2/token', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: body
    });
    const d = await r.json();
    if (d.id_token) sessionStorage.setItem('qf_token', d.id_token);
    else $('autherr').textContent = 'Sign-in failed. Please try again.';
  } catch (e) { $('autherr').textContent = 'Sign-in failed. Please try again.'; }
  history.replaceState({}, '', CFG.redirect);
}

function logout() {
  sessionStorage.clear();
  location.href = 'https://' + CFG.domain + '/logout?client_id=' + CFG.clientId
    + '&logout_uri=' + encodeURIComponent(CFG.redirect);
}

async function api(path, opts) {
  opts = opts || {};
  opts.headers = Object.assign({'Authorization': 'Bearer ' + token}, opts.headers || {});
  const r = await fetch(path, opts);
  if (r.status === 401) { sessionStorage.removeItem('qf_token'); location.reload(); }
  return r;
}

document.querySelectorAll('.type').forEach(el => {
  el.onclick = () => {
    document.querySelectorAll('.type').forEach(x => x.classList.remove('sel'));
    el.classList.add('sel');
    type = el.dataset.type;
  };
});

function render(status, id, secs) {
  $('result').classList.remove('hide');
  $('rid').textContent = id;
  $('badge').textContent = status;
  $('badge').className = 'badge ' + status;
  const prog = {PENDING: 1, PROCESSING: 2, DONE: 4, FAILED: 0}[status] || 0;
  [1, 2, 3].forEach(k => {
    $('s' + k).className = 'step' + (prog > k ? ' done' : (prog === k ? ' on' : ''));
  });
  const text = {
    PENDING: 'Your request is safely in line and will be picked up shortly.',
    PROCESSING: 'A worker is handling your request right now.',
    DONE: 'All done' + (secs !== null && secs !== undefined ? ' in ' + secs + ' seconds.' : '.'),
    FAILED: 'Something went wrong. Please submit again.'
  };
  $('msg').textContent = text[status] || '';
}

function watch(id) {
  clearInterval(timer);
  const tick = async () => {
    try {
      const r = await api('/status?id=' + encodeURIComponent(id));
      if (!r.ok) { clearInterval(timer); return; }
      const s = await r.json();
      render(s.status, id, s.seconds);
      if (s.status === 'DONE' || s.status === 'FAILED') { clearInterval(timer); loadMine(); }
    } catch (e) {}
  };
  tick();
  timer = setInterval(tick, 1500);
}

async function send() {
  $('err').textContent = '';
  const b = $('go');
  b.disabled = true; b.textContent = 'Submitting...';
  try {
    const r = await api('/submit', {
      method: 'POST',
      body: JSON.stringify({type: type, notify: $('notify').checked})
    });
    const d = await r.json();
    if (!r.ok) { $('err').textContent = d.error || 'Something went wrong.'; }
    else { watch(d.requestId); setTimeout(loadMine, 1500); }
  } catch (e) {
    $('err').textContent = 'Network error. Please try again.';
  }
  b.disabled = false; b.textContent = 'Submit request';
}

async function loadMine() {
  try {
    const r = await api('/my');
    if (!r.ok) return;
    const d = await r.json();
    const box = $('mine');
    box.textContent = '';
    if (!d.items.length) { box.textContent = 'No requests yet.'; return; }
    d.items.forEach(it => {
      const row = document.createElement('div');
      row.className = 'mrow';
      const a = document.createElement('span');
      a.textContent = LABEL[it.type] || it.type;
      const s = document.createElement('span');
      s.className = 'badge ' + it.status;
      s.textContent = it.status;
      row.appendChild(a); row.appendChild(s);
      row.onclick = () => watch(it.requestId);
      box.appendChild(row);
    });
  } catch (e) {}
}

async function stats() {
  if (document.hidden) return;
  try {
    const r = await api('/stats');
    if (!r.ok) return;
    const s = await r.json();
    $('wait').textContent = s.waiting;
    $('busy').textContent = s.processing;
    $('bar').style.width = Math.min(100, (s.waiting + s.processing) / 10) + '%';
  } catch (e) {}
}

(async function init() {
  const p = new URLSearchParams(location.search);
  if (p.get('code')) await finishLogin(p.get('code'));
  token = sessionStorage.getItem('qf_token');
  const c = token ? claims(token) : {};
  if (!token || !c.exp || c.exp * 1000 < Date.now()) {
    sessionStorage.removeItem('qf_token');
    return;
  }
  $('login').classList.add('hide');
  $('app').classList.remove('hide');
  $('who').classList.remove('hide');
  $('me').textContent = (c.name || c.email) + ' (' + c.email + ')';
  $('mail').textContent = c.email;
  loadMine();
  stats();
  setInterval(stats, 5000);
})();
</script></body></html>"""

def page():
    return (PAGE.replace("__COGNITO_DOMAIN__", os.environ["COGNITO_DOMAIN"])
                .replace("__CLIENT_ID__", os.environ["CLIENT_ID"])
                .replace("__REDIRECT_URI__", os.environ["REDIRECT_URI"]))

def reply(code, body, ctype="application/json"):
    return {"statusCode": code,
            "headers": {"Content-Type": ctype},
            "body": body if isinstance(body, str) else json.dumps(body)}

def who(event):
    """Identity comes only from the token that API Gateway already verified."""
    auth = event.get("requestContext", {}).get("authorizer") or {}
    c = (auth.get("jwt") or {}).get("claims") or {}
    email = str(c.get("email", "")).strip().lower()
    if not email or str(c.get("email_verified", "")).lower() != "true":
        return None, None
    name = str(c.get("name", "")).strip() or email.split("@")[0]
    return email, name[:100]

def view(item):
    secs = None
    if item.get("status") == "DONE" and "updatedAt" in item:
        secs = int(item["updatedAt"]) - int(item["createdAt"])
    return {"requestId": item["requestId"], "status": item["status"],
            "type": item["type"], "seconds": secs}

def handler(event, context):
    http = event["requestContext"]["http"]
    method, path = http["method"], http["path"]

    if method == "GET" and path == "/":
        return reply(200, page(), "text/html")

    email, name = who(event)
    if not email:
        return reply(401, {"error": "please sign in"})

    if method == "POST" and path == "/submit":
        try:
            data = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return reply(400, {"error": "invalid JSON"})
        rtype = str(data.get("type", "")).strip()
        if rtype not in TYPES:
            return reply(400, {"error": "a valid request type is required"})
        rid = str(uuid.uuid4())
        now = int(time.time())
        item = {"requestId": rid, "owner": email, "name": name, "type": rtype,
                "notify": bool(data.get("notify", False)), "status": "PENDING",
                "createdAt": now, "ttl": now + TTL_DAYS * 86400}
        table.put_item(Item=item)
        try:
            sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps({"requestId": rid}))
        except Exception as e:
            print("QUEUE FAILED", repr(e))
            item["status"] = "FAILED"
            table.put_item(Item=item)
            return reply(503, {"error": "We could not queue your request. Please try again."})
        return reply(202, {"requestId": rid, "status": "PENDING"})

    if method == "GET" and path == "/status":
        rid = (event.get("queryStringParameters") or {}).get("id", "")
        item = table.get_item(Key={"requestId": rid}).get("Item") if rid else None
        if not item or item.get("owner") != email:
            return reply(404, {"error": "not found"})
        return reply(200, view(item))

    if method == "GET" and path == "/my":
        res = table.query(IndexName="owner-index",
                          KeyConditionExpression=Key("owner").eq(email),
                          ScanIndexForward=False, Limit=10)
        return reply(200, {"items": [view(i) for i in res["Items"]]})

    if method == "GET" and path == "/stats":
        try:
            a = sqs.get_queue_attributes(
                QueueUrl=QUEUE_URL,
                AttributeNames=["ApproximateNumberOfMessages",
                                "ApproximateNumberOfMessagesNotVisible"])["Attributes"]
        except Exception as e:
            print("STATS FAILED", repr(e))
            return reply(503, {"error": "stats unavailable"})
        return reply(200, {"waiting": int(a["ApproximateNumberOfMessages"]),
                           "processing": int(a["ApproximateNumberOfMessagesNotVisible"])})

    return reply(404, {"error": "not found"})
