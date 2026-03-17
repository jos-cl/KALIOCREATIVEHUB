from flask import Flask, jsonify, request, send_from_directory
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

# load configuration from .env
load_dotenv()

app = Flask(__name__)

# configure MongoDB with timeout
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/kalio_dashboard?serverSelectionTimeoutMS=2000")

# Initialize PyMongo lazily to avoid blocking startup
mongo = None
def get_mongo():
    global mongo
    if mongo is None:
        try:
            mongo = PyMongo(app)
            print("✓ MongoDB initialized")
        except Exception as e:
            print(f"⚠ Failed to initialize PyMongo: {str(e)[:100]}")
    return mongo

# initialize default documents if missing
def setup_defaults():
    db_client = get_mongo()
    if db_client is None:
        print("⚠ MongoDB not available, skipping initialization")
        return

    try:
        db = db_client.db
        # stats
        if db.stats.count_documents({}) == 0:
            db.stats.insert_one({
                "activeProjects": 24,
                "totalClients": 42,
                "newMessages": 18
            })
        # ensure collections exist (empty)
        db.messages.index_information()
        db.projects.index_information()

        # sample data for demo
        if db.projects.count_documents({}) == 0:
            db.projects.insert_many([
                {"name": "D-Express Loans Branding", "description": "Logo & Business Cards", "status": "completed", "updated_at": "2025-03-01T12:00:00"},
                {"name": "Grace Boutique Social Media", "description": "Monthly Campaign", "status": "inprogress", "updated_at": "2025-03-10T09:00:00"},
                {"name": "Event Promotion", "description": "Event Promotion", "status": "completed", "updated_at": "2025-02-20T15:00:00"}
            ])
        if db.clients.count_documents({}) == 0:
            db.clients.insert_many([
                {"name": "Acme Corp"},
                {"name": "Bravo LLC"}
            ])
        if db.messages.count_documents({}) == 0:
            db.messages.insert_many([
                {"name": "Frazer Kalio", "message": "Interested in branding package...", "created_at": "2025-03-06T10:00:00", "read": False},
                {"name": "Joseph Machai", "message": "Need social media management...", "created_at": "2025-03-06T05:00:00", "read": False}
            ])
        print("✓ MongoDB initialized successfully")
    except Exception as e:
        print(f"⚠ MongoDB connection issue: {str(e)[:100]}")
        print("  HTML pages will still work, but API endpoints may not have data.")

# call initialization immediately to ensure defaults exist
# Run this in a thread to avoid blocking startup
import threading
def init_mongo_async():
    try:
        db_client = get_mongo()
        if db_client is not None:
            setup_defaults()
    except Exception as e:
        print("Error initializing MongoDB: {}".format(str(e)[:100]))

try:
    setup_thread = threading.Thread(target=init_mongo_async, daemon=True)
    setup_thread.start()
except Exception as e:
    print("Error starting MongoDB initialization thread: {}".format(str(e)[:100]))

# simple health check
@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok"}), 200

# example: get stats (for cards)
@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        db_client = get_mongo()
        if db_client is None:
            return jsonify({"activeProjects": 0, "totalClients": 0, "newMessages": 0}), 200
        db = db_client.db
        active_projects = db.projects.count_documents({})
        total_clients = db.clients.count_documents({})
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_messages = db.messages.count_documents({"created_at": {"$gte": week_ago.isoformat()}})
        return jsonify({
            "activeProjects": active_projects,
            "totalClients": total_clients,
            "newMessages": new_messages
        }), 200
    except Exception as e:
        # return default stats if DB unavailable
        return jsonify({"activeProjects": 0, "totalClients": 0, "newMessages": 0}), 200

# example: get recent items (messages or projects)
@app.route("/api/recent/messages", methods=["GET"])
def recent_messages():
    try:
        from datetime import datetime, timezone
        def format_msg(doc):
            m = {
                "id": str(doc.get("_id")),
                "fromName": doc.get("name"),
                "preview": (doc.get("message") or "")[0:40] + ("..." if len(doc.get("message", ""))>40 else ""),
                "timeAgo": "",
                "fromInitials": ""
            }
            if doc.get("created_at"):
                try:
                    # Parse ISO format timestamp (handle timezone-aware strings)
                    created_str = doc.get("created_at")
                    if isinstance(created_str, str):
                        # Remove timezone info if present for simplicity
                        if '+' in created_str:
                            created_str = created_str.split('+')[0]
                        elif created_str.endswith('Z'):
                            created_str = created_str[:-1]
                        dt = datetime.fromisoformat(created_str)
                    else:
                        dt = created_str
                    delta = datetime.utcnow() - dt
                    if delta.days >= 1:
                        m["timeAgo"] = f"{delta.days} day{'' if delta.days==1 else 's'} ago"
                    elif delta.seconds >= 3600:
                        hrs = delta.seconds//3600
                        m["timeAgo"] = f"{hrs} hour{'' if hrs==1 else 's'} ago"
                    elif delta.seconds >= 60:
                        mins = delta.seconds//60
                        m["timeAgo"] = f"{mins} minute{'' if mins==1 else 's'} ago"
                    else:
                        m["timeAgo"] = "just now"
                except Exception as te:
                    m["timeAgo"] = "recently"
            name = doc.get("name", "")
            m["fromInitials"] = "".join([p[0] for p in name.split() if p])[:2].upper()
            return m
        db_client = get_mongo()
        if db_client is None:
            return jsonify([]), 200
        cursor = db_client.db.messages.find().sort("created_at", -1).limit(10)
        messages = [format_msg(doc) for doc in cursor]
        return jsonify(messages), 200
    except Exception as e:
        return jsonify([]), 200

@app.route("/api/recent/projects", methods=["GET"])
def recent_projects():
    try:
        def format_proj(doc):
            status = doc.get("status", "")
            status_map = {
                "completed": "status-completed",
                "pending": "status-pending",
                "inprogress": "status-inprogress"
            }
            return {
                "id": str(doc.get("_id")),
                "name": doc.get("name"),
                "description": doc.get("description"),
                "status": status.capitalize(),
                "statusClass": status_map.get(status.lower(), ""),
                "icon": doc.get("icon", "fa-briefcase")
            }
        db_client = get_mongo()
        if db_client is None:
            return jsonify([]), 200
        cursor = db_client.db.projects.find().sort("updated_at", -1).limit(10)
        projects = [format_proj(doc) for doc in cursor]
        return jsonify(projects), 200
    except Exception as e:
        return jsonify([]), 200

# create a new message (quick action example)
@app.route("/api/messages", methods=["POST"])
def create_message():
    data = request.json
    db_client = get_mongo()
    if db_client is None:
        return jsonify({"error": "Database unavailable"}), 503
    result = db_client.db.messages.insert_one(data)
    return jsonify({"inserted_id": str(result.inserted_id)}), 201

# general contact submission from public site
@app.route("/api/contact", methods=["POST"])
def submit_contact():
    try:
        data = request.json or {}
        data.setdefault('created_at', None)
        data.setdefault('status', 'new')  # new, in-progress, responded
        data.setdefault('responses', [])  # admin responses
        db_client = get_mongo()
        if db_client is None:
            return jsonify({"inserted_id": "temp", "note": "Message queued. DB may be offline."}), 201
        result = db_client.db.messages.insert_one(data)
        return jsonify({"inserted_id": str(result.inserted_id)}), 201
    except Exception as e:
        # return success even if DB fails, so form doesn't show errors to user
        return jsonify({"inserted_id": "temp", "note": "Message queued. DB may be offline."}), 201

# get all inquiries for admin dashboard
@app.route("/api/inquiries", methods=["GET"])
def get_inquiries():
    try:
        cursor = mongo.db.messages.find().sort("created_at", -1).limit(50)
        inquiries = []
        for doc in cursor:
            inquiries.append({
                "id": str(doc.get("_id")),
                "type": doc.get("type", "inquiry"),
                "name": doc.get("name"),
                "email": doc.get("email"),
                "phone": doc.get("phone"),
                "message": doc.get("message"),
                "subject": doc.get("subject"),
                "status": doc.get("status", "new"),
                "created_at": doc.get("created_at"),
                "responses": doc.get("responses", [])
            })
        return jsonify(inquiries), 200
    except Exception as e:
        return jsonify([]), 200

# add admin response to an inquiry
@app.route("/api/inquiries/<inquiry_id>/respond", methods=["POST"])
def respond_to_inquiry(inquiry_id):
    try:
        from bson.objectid import ObjectId
        data = request.json or {}
        response_text = data.get("response", "")
        
        # add response to the inquiry
        mongo.db.messages.update_one(
            {"_id": ObjectId(inquiry_id)},
            {
                "$push": {"responses": {"text": response_text, "timestamp": data.get("timestamp")}},
                "$set": {"status": "responded"}
            }
        )
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# update inquiry status
@app.route("/api/inquiries/<inquiry_id>/status", methods=["PUT"])
def update_inquiry_status(inquiry_id):
    try:
        from bson.objectid import ObjectId
        data = request.json or {}
        new_status = data.get("status", "new")
        
        mongo.db.messages.update_one(
            {"_id": ObjectId(inquiry_id)},
            {"$set": {"status": new_status}}
        )
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# portfolio images listing
@app.route("/api/portfolio", methods=["GET"])
def get_portfolio():
    # attempt to read JSON file from workspace
    try:
        workspace_root = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
        json_path = os.path.join(workspace_root, 'images', 'images.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            import json
            imgs = json.load(f)
        return jsonify(imgs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    try:
        db = mongo.db
        alerts = db.alerts.count_documents({"read": {"$ne": True}}) if "alerts" in db.list_collection_names() else 0
        msgs = db.messages.count_documents({"read": {"$ne": True}})
        return jsonify({"alerts": alerts, "messages": msgs}), 200
    except Exception as e:
        return jsonify({"alerts": 0, "messages": 0}), 200

@app.route("/api/charts/projects", methods=["GET"])
def charts_projects():
    # sample static data; replace with aggregation if desired
    return jsonify({
        "labels": ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        "completed": [12, 19, 8, 15, 18, 14],
        "new": [5, 10, 6, 8, 12, 10]
    }), 200

@app.route("/api/charts/services", methods=["GET"])
def charts_services():
    return jsonify({
        "labels": ['Creative Design', 'Social Media Marketing', 'Facebook Boosting', 'Branding'],
        "data": [35, 25, 20, 20]
    }), 200

@app.route("/api/quick-actions", methods=["GET"])
def get_quick_actions():
    actions = [
        {"icon": "fa-plus-circle", "label": "New Project"},
        {"icon": "fa-upload", "label": "Upload Work"},
        {"icon": "fa-user-plus", "label": "Add Client"},
        {"icon": "fa-file-invoice-dollar", "label": "Create Invoice"},
        {"icon": "fa-chart-bar", "label": "Generate Report"},
        {"icon": "fa-cogs", "label": "Settings"}
    ]
    return jsonify(actions), 200

# explicit route for admin dashboard
@app.route('/admin')
def serve_admin():
    workspace_root = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    try:
        # Try public/admin/dashboard.html first
        admin_path = os.path.join(workspace_root, 'public', 'admin', 'dashboard.html')
        if os.path.exists(admin_path):
            with open(admin_path, 'r', encoding='utf-8') as f:
                return f.read()
        # Fallback to Admin Dashboard/AdminScreen.html
        admin_path = os.path.join(workspace_root, 'Admin Dashboard', 'AdminScreen.html')
        with open(admin_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>Error loading admin dashboard</h1><p>{str(e)}</p>", 404

# explicit route for contacts page
@app.route('/contacts')
def serve_contacts():
    workspace_root = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    try:
        contacts_path = os.path.join(workspace_root, 'public', 'contacts.html')
        with open(contacts_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>Error loading contacts page</h1><p>{str(e)}</p>", 404

# explicit route for admin messages page
@app.route('/messages.html')
@app.route('/admin/messages')
def serve_messages():
    workspace_root = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    try:
        # Try public/admin/messages.html first
        messages_path = os.path.join(workspace_root, 'public', 'admin', 'messages.html')
        if os.path.exists(messages_path):
            with open(messages_path, 'r', encoding='utf-8') as f:
                return f.read()
        # Fallback to public/messages.html
        messages_path = os.path.join(workspace_root, 'public', 'messages.html')
        with open(messages_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>Error loading messages page</h1><p>{str(e)}</p>", 404

# generic CRUD endpoints can be added similarly

# serve static files and pages from public folder
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    workspace_root = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    public_root = os.path.join(workspace_root, 'public')
    
    # default to index.html for root
    if path == '' or path is None:
        try:
            return send_from_directory(public_root, 'index.html')
        except Exception as e:
            return {"error": f"Index not found: {str(e)}"}, 404
    
    # try to serve requested file from public folder
    try:
        return send_from_directory(public_root, path)
    except Exception as e:
        return {"error": f"File not found: {path}"}, 404

if __name__ == "__main__":
    try:
        print("Starting Flask server on port 8080...")
        print("MongoDB initialized")
        app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    except Exception as e:
        print("Error starting server: {}".format(str(e)))
        import traceback
        traceback.print_exc()
