from HandyHub.Handy import create_app
from flask import Flask

app = Flask(__name__)
# your other setup like routes, configs, etc.

if __name__ == "__main__":
    app.run(debug=True)
