#!/usr/bin/env python
import sys
print("Python: {}".format(sys.version))
print("Python executable: {}".format(sys.executable))

print("\n1. Testing imports...")
try:
    from flask import Flask
    print("[OK] Flask imported")
except Exception as e:
    print("[ERROR] Flask error: {}".format(e))
    sys.exit(1)

try:
    import pymongo
    print("[OK] PyMongo imported")
except Exception as e:
    print("[ERROR] PyMongo error: {}".format(e))
    sys.exit(1)

try:
    from flask_pymongo import PyMongo
    print("[OK] Flask-PyMongo imported")
except Exception as e:
    print("[ERROR] Flask-PyMongo error: {}".format(e))
    sys.exit(1)

print("\n2. Testing app creation...")
try:
    from app import app
    print("[OK] App imported successfully")
except Exception as e:
    print("[ERROR] App import error: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. Testing server startup...")
try:
    print("Starting server on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
except Exception as e:
    print("[ERROR] Server error: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
