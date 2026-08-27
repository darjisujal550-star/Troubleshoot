from flask import Flask, request, redirect, render_template_string, session, url_for, send_from_directory
import sqlite3, smtplib, os, uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
DATABASE = "guni_troubleshooter.db"
UPLOAD_FOLDER = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.secret_key = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ROLES = {
    "mentor": {"name": "Mentor", "username": "mentor", "password": "GUNI@123"},
    "hod": {"name": "HOD", "username": "hod", "password": "HOD@123"},
    "principal": {"name": "Principal", "username": "principal", "password": "PRINCIPAL@123"}
}

# Replace these before enabling real email.
SENDER_EMAIL = "yourgmail@gmail.com"
GMAIL_APP_PASSWORD = "YOUR_16_DIGIT_APP_PASSWORD"
# Email address for each complaint recipient.
# The selected recipient on the student form determines which address receives the complaint.
RECIPIENT_EMAILS = {
    "mentor": "mentor4566@gamil.com",
    "hod": "hod113003@gmail.com",
    "principal": "principalguni@gmail.com"
}

IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
VIDEO_EXT = {"mp4", "webm", "mov", "avi", "mkv"}
ALLOWED_EXT = IMAGE_EXT | VIDEO_EXT

def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            enrollment TEXT NOT NULL,
            description TEXT NOT NULL,
            recipient TEXT DEFAULT 'mentor',
            is_anonymous INTEGER DEFAULT 0,
            solution TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("PRAGMA table_info(problems)")
    cols = [r[1] for r in cur.fetchall()]
    if "recipient" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN recipient TEXT DEFAULT 'mentor'")
    if "is_anonymous" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN is_anonymous INTEGER DEFAULT 0")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_name TEXT,
            file_type TEXT,
            FOREIGN KEY(problem_id) REFERENCES problems(id)
        )
    """)
    conn.commit()
    conn.close()

def allowed_file(filename):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT)

def file_type(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    return "image" if ext in IMAGE_EXT else "video"

def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get(role + "_logged_in"):
                return redirect(url_for(role + "_login"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def send_email(name, enrollment, description, recipient, attachments):
    # Send the complaint only to the role selected by the student.
    to_email = RECIPIENT_EMAILS.get(recipient)
    if not to_email:
        return False
    msg = MIMEMultipart()
    msg["Subject"] = "New Student Complaint - GUNI Trouble-Shooter"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    body = f"""GUNI TROUBLE-SHOOTER

A new complaint was submitted.

Sent to: {ROLES[recipient]["name"]}
Student: {name}
Enrollment: {enrollment}

Problem:
{description}

Uploaded evidence: {len(attachments)} file(s)
"""
    msg.attach(MIMEText(body, "plain"))
    for a in attachments:
        path = os.path.join(UPLOAD_FOLDER, a["filename"])
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=a["original_name"])
            msg.attach(part)
        except Exception as e:
            print("Attachment email error:", e)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Email Error:", e)
        return False

HOME_PAGE = """
<!doctype html><html><head><title>GUNI Trouble-Shooter</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{
    box-sizing:border-box;
}

html{
    scroll-behavior:smooth;
}

body{
    margin:0;
    font-family:Arial, Helvetica, sans-serif;
    background:#f4f7fb;
    color:#172033;
}

/* =========================
   HEADER
========================= */

header{
    background:linear-gradient(
        135deg,
        #172554,
        #1e40af,
        #2563eb
    );

    color:white;
    text-align:center;

    padding:45px 20px 50px;

    box-shadow:
        0 8px 30px rgba(0,0,0,0.15);
}

header h1{
    margin:0 0 22px;

    font-size:40px;
    font-weight:800;

    letter-spacing:0.3px;
}

header p{
    margin:22px 0 0;

    font-size:18px;
    font-weight:500;

    color:#e0e7ff;
}

/* =========================
   GUNI IMAGE
========================= */

.guni-image{
    display:block;

    width:260px;
    max-width:85%;

    height:auto;

    margin:0 auto;

    border-radius:18px;

    border:4px solid rgba(255,255,255,0.9);

    box-shadow:
        0 12px 35px rgba(0,0,0,0.28);

    transition:
        transform 0.3s ease,
        box-shadow 0.3s ease;
}

.guni-image:hover{
    transform:scale(1.03);

    box-shadow:
        0 16px 40px rgba(0,0,0,0.35);
}

/* =========================
   MAIN CONTAINER
========================= */

.container{
    width:92%;
    max-width:900px;

    margin:45px auto;

    padding:0 10px;
}

/* =========================
   CARDS
========================= */

.card{
    background:white;

    padding:32px;

    margin-bottom:28px;

    border-radius:20px;

    border:1px solid #e2e8f0;

    box-shadow:
        0 8px 30px rgba(15,23,42,0.08);

    transition:
        transform 0.2s ease,
        box-shadow 0.2s ease;
}

.card:hover{
    transform:translateY(-2px);

    box-shadow:
        0 12px 35px rgba(15,23,42,0.12);
}

/* =========================
   HEADINGS
========================= */

h2{
    margin-top:0;

    margin-bottom:25px;

    color:#1e3a8a;

    font-size:25px;
}

h3{
    color:#1e3a8a;
}

/* =========================
   LABELS
========================= */

label{
    display:block;

    margin-top:18px;
    margin-bottom:8px;

    font-weight:700;

    color:#334155;
}

/* =========================
   INPUTS
========================= */

input,
textarea,
select{
    width:100%;

    padding:14px 15px;

    border:1px solid #cbd5e1;

    border-radius:10px;

    background:#f8fafc;

    color:#172033;

    font-size:15px;

    outline:none;

    transition:
        border-color 0.2s ease,
        box-shadow 0.2s ease,
        background 0.2s ease;
}

input:focus,
textarea:focus,
select:focus{
    border-color:#2563eb;

    background:white;

    box-shadow:
        0 0 0 3px rgba(37,99,235,0.12);
}

textarea{
    min-height:150px;

    resize:vertical;
}

select{
    cursor:pointer;
}

/* =========================
   RADIO OPTIONS
========================= */

.radio{
    display:flex;

    gap:12px;

    flex-wrap:wrap;

    margin-top:10px;
}

.radio label{
    display:flex;

    align-items:center;

    gap:7px;

    margin:0;

    padding:10px 15px;

    background:#f1f5f9;

    border:1px solid #e2e8f0;

    border-radius:9px;

    cursor:pointer;

    font-weight:600;
}

.radio input{
    width:auto;

    margin:0;

    cursor:pointer;
}

/* =========================
   INFORMATION BOX
========================= */

.info{
    background:#eff6ff;

    color:#1e40af;

    padding:14px 16px;

    margin-top:15px;

    border-left:4px solid #2563eb;

    border-radius:9px;

    line-height:1.5;

    font-size:14px;
}

/* =========================
   FILE UPLOAD
========================= */

input[type="file"]{
    background:white;

    padding:12px;

    cursor:pointer;
}

/* =========================
   BUTTON
========================= */

button{
    width:100%;

    margin-top:24px;

    padding:15px 20px;

    border:0;

    border-radius:10px;

    background:linear-gradient(
        135deg,
        #2563eb,
        #1d4ed8
    );

    color:white;

    font-size:16px;

    font-weight:700;

    cursor:pointer;

    box-shadow:
        0 6px 15px rgba(37,99,235,0.25);

    transition:
        transform 0.2s ease,
        box-shadow 0.2s ease,
        background 0.2s ease;
}

button:hover{
    background:linear-gradient(
        135deg,
        #1d4ed8,
        #1e40af
    );

    transform:translateY(-2px);

    box-shadow:
        0 9px 20px rgba(37,99,235,0.32);
}

button:active{
    transform:translateY(0);
}

/* =========================
   STATUS SECTION
========================= */

.status-card{
    border-left:5px solid #2563eb;
}

/* =========================
   MENTOR / STAFF SECTION
========================= */

.staff{
    text-align:center;
}

.staff a{
    display:inline-block;

    margin-top:8px;

    padding:12px 20px;

    background:#eef2ff;

    color:#1e40af;

    border:1px solid #c7d2fe;

    border-radius:9px;

    text-decoration:none;

    font-weight:700;

    transition:
        background 0.2s ease,
        transform 0.2s ease;
}

.staff a:hover{
    background:#e0e7ff;

    transform:translateY(-2px);
}

/* =========================
   FOOTER
========================= */

footer{
    text-align:center;

    padding:35px 20px;

    margin-top:50px;

    background:#172554;

    color:#cbd5e1;

    font-size:14px;
}

/* =========================
   MOBILE
========================= */

@media(max-width:600px){

    header{
        padding:35px 15px 40px;
    }

    header h1{
        font-size:28px;
    }

    header p{
        font-size:16px;
    }

    .guni-image{
        width:220px;
    }

    .container{
        width:94%;

        margin:30px auto;
    }

    .card{
        padding:22px;

        border-radius:16px;
    }

    h2{
        font-size:21px;
    }

    .radio{
        flex-direction:column;
    }

    .radio label{
        width:100%;
    }

}
</style></head><body>
<header><h1>🎓 GUNI Trouble-Shooter</h1>
<img 
     src="{{ url_for('static', filename='guni.jpg') }}"
     alt="GUNI"
     class="guni-image">
<p>Student Problem? We'll Help You Solve It.</p></header>
<div class="container">
<div class="card"><h2>📝 Submit Your Problem</h2>
<form action="/submit" method="POST" enctype="multipart/form-data">
<label>Student Name</label>
<input type="text" name="name" id="studentName" placeholder="Enter your name">
<label>Name Privacy</label>
<div class="radio">
<label><input type="radio" name="anonymous" value="no" checked onclick="setName(true)"> Reveal my name</label>
<label><input type="radio" name="anonymous" value="yes" onclick="setName(false)"> Keep my name secret</label>
</div>
<div class="info">🔐 With secret mode, the recipient sees <b>Anonymous Student</b>.</div>
<label>Enrollment Number</label>
<input type="text" name="enrollment" required placeholder="Enter enrollment number">
<label>Send Complaint To</label>
<select name="recipient" required>
<option value="">-- Select Recipient --</option>
<option value="mentor">👨‍🏫 Mentor</option>
<option value="hod">👨‍💼 HOD</option>
<option value="principal">👨‍💼 Principal</option>
</select>
<label>Problem Description</label>
<textarea name="description" rows="7" required placeholder="Describe your problem..."></textarea>
<label>📷 Photo / 🎥 Video Evidence</label>
<input type="file" name="attachments" accept="image/*,video/*" multiple>
<div class="info">You can upload photos or short videos. Maximum total upload size: <b>50 MB</b>.</div>
<button type="submit">🚀 Submit Problem</button>
</form></div>
<div class="card"><h2>🔍 Check Problem Status</h2>
<form action="/status" method="GET">
<label>Enrollment Number</label><input type="text" name="enrollment" required>
<button type="submit">Check Status</button></form></div>
<div class="card staff"><h2>🔐 Staff Login</h2>
<a href="/mentor/login">Mentor</a><a href="/hod/login">HOD</a><a href="/principal/login">Principal</a></div>
</div><footer>GUNI Trouble-Shooter © 2026</footer>
<script>
function setName(show){let x=document.getElementById("studentName");x.disabled=!show;x.required=show;if(!show){x.value="";x.placeholder="Your name will remain secret"}else{x.placeholder="Enter your name"}}
</script></body></html>
"""

@app.route("/")
def home():
    return render_template_string(HOME_PAGE)

@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    enrollment = request.form.get("enrollment", "").strip()
    description = request.form.get("description", "").strip()
    recipient = request.form.get("recipient", "").strip()
    anonymous = request.form.get("anonymous", "no").strip()

    if not enrollment or not description:
        return "Enrollment number and problem description are required.", 400
    if recipient not in ROLES:
        return "Please select a valid recipient.", 400

    if anonymous == "yes":
        display_name, is_anonymous = "Anonymous Student", 1
    else:
        if not name:
            return "Enter your name or choose Keep my name secret.", 400
        display_name, is_anonymous = name, 0

    files = []
    for f in request.files.getlist("attachments"):
        if f and f.filename:
            if not allowed_file(f.filename):
                return "Invalid file type. Upload an image or video.", 400
            files.append(f)

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""INSERT INTO problems
        (name,enrollment,description,recipient,is_anonymous)
        VALUES (?,?,?,?,?)""",
        (display_name,enrollment,description,recipient,is_anonymous))
    problem_id = cur.lastrowid

    saved = []
    for f in files:
        original = secure_filename(f.filename)
        ext = original.rsplit(".", 1)[1].lower()
        unique = f"{uuid.uuid4()}.{ext}"
        f.save(os.path.join(UPLOAD_FOLDER, unique))
        typ = file_type(original)
        cur.execute("""INSERT INTO attachments
            (problem_id,filename,original_name,file_type)
            VALUES (?,?,?,?)""",
            (problem_id,unique,original,typ))
        saved.append({"filename":unique,"original_name":original,"file_type":typ})

    conn.commit()
    conn.close()
    send_email(display_name,enrollment,description,recipient,saved)

    return render_template_string(SUCCESS_PAGE,
        enrollment=enrollment,
        recipient=ROLES[recipient]["name"],
        problem_id=problem_id)

SUCCESS_PAGE = """
<!doctype html><html><head><title>Submitted</title><style>
body{font-family:Arial;background:#eef2ff;text-align:center;padding:70px 20px}.box{background:white;max-width:550px;margin:auto;padding:40px;border-radius:18px}a{display:inline-block;margin:10px;padding:12px 20px;background:#4f46e5;color:white;text-decoration:none;border-radius:8px}
</style></head><body><div class="box">
<h1>✅ Problem Submitted!</h1><p>Your complaint was saved successfully.</p>
<p><b>Sent to:</b> {{recipient}}</p><p><b>Problem ID:</b> #{{problem_id}}</p>
<a href="/status?enrollment={{enrollment}}">Check Status</a><br><a href="/">Back to Home</a>
</div></body></html>
"""

STATUS_PAGE = """
<!doctype html><html><head><title>Problem Status</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;font-family:Arial;background:#f1f5f9}.container{max-width:850px;margin:40px auto;padding:20px}.card{background:white;padding:25px;margin-bottom:20px;border-radius:15px;box-shadow:0 5px 20px #00000012}.pending{color:#d97706;font-weight:bold}.solved{color:#16a34a;font-weight:bold}.solution{background:#ecfdf5;padding:15px;border-radius:10px}.media{background:#f8fafc;padding:15px;border-radius:12px;margin-top:18px}.media img{max-width:100%;max-height:500px;display:block;margin:15px auto;border-radius:10px}.media video{width:100%;max-height:500px;display:block;margin:15px auto;border-radius:10px}a{color:#4f46e5}
</style></head><body><div class="container">
<h1>📋 Problem Status</h1><p>Enrollment: <b>{{enrollment}}</b></p>
{% if problems %}{% for item in problems %}{% set p=item.problem %}
<div class="card"><h2>Problem #{{p.id}}</h2>
<p><b>Student:</b> {% if p.is_anonymous %}Anonymous Student{% else %}{{p.name}}{% endif %}</p>
<p><b>Complaint Sent To:</b> {{p.recipient|capitalize}}</p>
<p><b>Problem:</b> {{p.description}}</p>
<p><b>Status:</b> {% if p.status=="Solved" %}<span class="solved">Solved</span>{% else %}<span class="pending">Pending</span>{% endif %}</p>
{% if item.attachments %}<div class="media"><h3>📷 Complaint Evidence</h3>
{% for f in item.attachments %}
{% if f.file_type=="image" %}<img src="{{url_for('uploaded_file',filename=f.filename)}}" alt="Complaint evidence">
{% else %}<video controls><source src="{{url_for('uploaded_file',filename=f.filename)}}">Your browser does not support video playback.</video>{% endif %}
<p>📎 {{f.original_name}}</p>{% endfor %}</div>{% endif %}
{% if p.solution %}<div class="solution"><h3>✅ Solution</h3><p>{{p.solution}}</p></div>
{% else %}<p>⏳ The selected recipient has not replied yet.</p>{% endif %}
</div>{% endfor %}
{% else %}<div class="card"><h2>❌ No Problems Found</h2><p>No problem was found for this enrollment number.</p></div>{% endif %}
<a href="/">← Back to Home</a></div></body></html>
"""

@app.route("/status")
def status():
    enrollment = request.args.get("enrollment", "").strip()
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM problems WHERE enrollment=? ORDER BY id DESC", (enrollment,))
    problems = cur.fetchall()
    data = []
    for p in problems:
        cur.execute("SELECT * FROM attachments WHERE problem_id=? ORDER BY id", (p["id"],))
        data.append({"problem": p, "attachments": cur.fetchall()})
    conn.close()
    return render_template_string(STATUS_PAGE, problems=data, enrollment=enrollment)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

LOGIN_PAGE = """
<!doctype html><html><head><title>{{role_name}} Login</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;font-family:Arial;background:linear-gradient(135deg,#312e81,#4f46e5)}.box{width:90%;max-width:430px;margin:100px auto;background:white;padding:35px;border-radius:18px;box-shadow:0 15px 40px #0003}h1{text-align:center;color:#312e81}label{display:block;margin-top:18px;font-weight:bold}input{width:100%;padding:13px;margin-top:7px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box}button{width:100%;padding:14px;margin-top:25px;border:0;border-radius:8px;background:#4f46e5;color:white;font-size:16px;font-weight:bold}.error{background:#fee2e2;color:#b91c1c;padding:10px;border-radius:8px;margin-top:15px;text-align:center}.back{text-align:center;margin-top:20px}.back a{color:#4f46e5}
</style></head><body><div class="box"><h1>🔐 {{role_name}} Login</h1>
<form method="POST"><label>Username</label><input type="text" name="username" required>
<label>Password</label><input type="password" name="password" required>
<button type="submit">Login as {{role_name}}</button></form>
{% if error %}<div class="error">{{error}}</div>{% endif %}
<div class="back"><a href="/">← Back to Website</a></div></div></body></html>
"""

def do_login(role):
    error = ""
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if u == ROLES[role]["username"] and p == ROLES[role]["password"]:
            for r in ROLES:
                session.pop(r + "_logged_in", None)
            session[role + "_logged_in"] = True
            return redirect(url_for(role + "_dashboard"))
        error = "Invalid username or password."
    return render_template_string(LOGIN_PAGE, role_name=ROLES[role]["name"], error=error)

@app.route("/mentor/login", methods=["GET","POST"])
def mentor_login(): return do_login("mentor")

@app.route("/hod/login", methods=["GET","POST"])
def hod_login(): return do_login("hod")

@app.route("/principal/login", methods=["GET","POST"])
def principal_login(): return do_login("principal")

def get_problems(role):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM problems WHERE recipient=? ORDER BY id DESC", (role,))
    problems = cur.fetchall()
    data = []
    for p in problems:
        cur.execute("SELECT * FROM attachments WHERE problem_id=? ORDER BY id", (p["id"],))
        data.append({"problem":p, "attachments":cur.fetchall()})
    conn.close()
    return data

DASHBOARD_PAGE = """
<!doctype html><html><head><title>{{role_name}} Dashboard</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;font-family:Arial;background:#f1f5f9}header{background:#312e81;color:white;padding:25px;text-align:center}.container{max-width:1000px;margin:30px auto;padding:20px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px}.logout{background:#dc2626;color:white;padding:10px 16px;border-radius:8px;text-decoration:none}.problem,.empty{background:white;padding:25px;margin-bottom:20px;border-radius:15px;box-shadow:0 5px 20px #00000012}textarea{width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box;margin-top:10px}button{background:#4f46e5;color:white;border:0;padding:12px 20px;margin-top:10px;border-radius:8px}.pending{color:#d97706;font-weight:bold}.solved{color:#16a34a;font-weight:bold}.solution{background:#ecfdf5;padding:15px;border-radius:10px}.media{margin-top:20px;background:#f8fafc;padding:15px;border-radius:12px}.media img{max-width:100%;max-height:500px;display:block;margin:15px auto;border-radius:10px}.media video{width:100%;max-height:500px;display:block;margin:15px auto;border-radius:10px}
</style></head><body>
<header><h1>👨‍💼 GUNI {{role_name}} Dashboard</h1><p>Student Problem Management</p></header>
<div class="container"><div class="top"><h2>{{role_name}} Complaints</h2><a class="logout" href="/{{role}}/logout">Logout</a></div>
{% if problems %}{% for item in problems %}{% set p=item.problem %}
<div class="problem"><h2>Problem #{{p.id}}</h2>
<p><b>Complaint Sent To:</b> {{role_name}}</p>
<p><b>Student Name:</b> {% if p.is_anonymous %}🔒 Anonymous Student{% else %}{{p.name}}{% endif %}</p>
<p><b>Enrollment Number:</b> {{p.enrollment}}</p>
<p><b>Problem:</b></p><p>{{p.description}}</p>
<p><b>Status:</b> {% if p.status=="Solved" %}<span class="solved">Solved</span>{% else %}<span class="pending">Pending</span>{% endif %}</p>
{% if item.attachments %}<div class="media"><h3>📷 Complaint Evidence</h3>
{% for f in item.attachments %}
{% if f.file_type=="image" %}<img src="{{url_for('uploaded_file',filename=f.filename)}}" alt="Complaint evidence">
{% else %}<video controls><source src="{{url_for('uploaded_file',filename=f.filename)}}">Your browser does not support video playback.</video>{% endif %}
<p>📎 {{f.original_name}}</p>{% endfor %}</div>{% endif %}
{% if p.status=="Pending" %}<form action="/{{role}}/solve/{{p.id}}" method="POST">
<textarea name="solution" rows="5" required placeholder="Write solution for the student..."></textarea>
<button type="submit">✅ Send Solution</button></form>
{% else %}<div class="solution"><h3>✅ Solution Sent</h3><p>{{p.solution}}</p></div>{% endif %}
</div>{% endfor %}
{% else %}<div class="empty"><h2>🎉 No {{role_name}} complaints yet.</h2><p>Complaints sent to {{role_name}} will appear here.</p></div>{% endif %}
</div></body></html>
"""

@app.route("/mentor")
@role_required("mentor")
def mentor_dashboard():
    return render_template_string(DASHBOARD_PAGE, role="mentor", role_name="Mentor", problems=get_problems("mentor"))

@app.route("/hod")
@role_required("hod")
def hod_dashboard():
    return render_template_string(DASHBOARD_PAGE, role="hod", role_name="HOD", problems=get_problems("hod"))

@app.route("/principal")
@role_required("principal")
def principal_dashboard():
    return render_template_string(DASHBOARD_PAGE, role="principal", role_name="Principal", problems=get_problems("principal"))

@app.route("/<role>/solve/<int:problem_id>", methods=["POST"])
def solve(role, problem_id):
    if role not in ROLES:
        return "Invalid role.", 404
    if not session.get(role + "_logged_in"):
        return redirect(url_for(role + "_login"))
    solution = request.form.get("solution", "").strip()
    if not solution:
        return "Solution cannot be empty.", 400
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""UPDATE problems SET solution=?,status='Solved'
                   WHERE id=? AND recipient=?""", (solution, problem_id, role))
    conn.commit()
    conn.close()
    return redirect(url_for(role + "_dashboard"))

@app.route("/<role>/logout")
def logout(role):
    if role not in ROLES:
        return "Invalid role.", 404
    session.pop(role + "_logged_in", None)
    return redirect(url_for(role + "_login"))

@app.errorhandler(413)
def too_large(error):
    return "Upload is too large. Maximum total upload size is 50 MB.", 413

if __name__ == "__main__":
    init_db()
    print("====================================")
    print("       GUNI TROUBLE-SHOOTER")
    print("====================================")
    print("Student:  http://127.0.0.1:5000")
    print("Mentor:   http://127.0.0.1:5000/mentor/login")
    print("HOD:      http://127.0.0.1:5000/hod/login")
    print("Principal: http://127.0.0.1:5000/principal/login")
    print()
    print("Mentor:    mentor / GUNI@123")
    print("HOD:       hod / HOD@123")
    print("Principal: principal / PRINCIPAL@123")
    print("====================================")
    app.run(debug=True,port=5000)
