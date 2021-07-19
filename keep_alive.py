from flask import Flask
from threading import Thread
from flask import send_file, send_from_directory, safe_join, abort
from flask import request
import os


app = Flask('')

@app.route('/')
def home():
  return("Alive")

@app.route('/log')
def log():
  ip_address = request.access_route[-1]
  if(str(ip_address) == os.environ.get("IP")):
    try:
      filename = "soundboard.csv"
      return send_file(filename)
    except Exception as e:
      return "404: File not found"
  else:
    return "No access"

@app.route('/camperlog')
def camperlog():
  ip_address = request.access_route[-1]
  if(request.method == "GET" and request.args.get('q') == os.environ.get("PASSWORD")):
    try:
      filename = "/home/ftpolav/camper/log.csv"
      return send_file(filename)
    except Exception as e:
      return abort(404)
  else:
    return abort(404)
 
@app.route('/powerbi')
def powerbi():
  ip_address = request.access_route[-1]
  if(request.method == "GET" and request.args.get('q') == os.environ.get("PASSWORD")):
    try:
      filename = "/home/ftpolav/camper/hours.csv"
      return send_file(filename)
    except Exception as e:
      return abort(404)
  else:
    return abort(404)

def run():
  app.run(host='185.189.182.43',port=8080)

def keep_alive():
  t = Thread(target=run)
  t.start()


