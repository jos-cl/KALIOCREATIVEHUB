from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Server is working!"

@app.route('/admin')
def admin():
    return "Admin page works!"

if __name__ == "__main__":
    print("Starting simple test server on port 8080...")
    app.run(host="0.0.0.0", port=8080, debug=False)
