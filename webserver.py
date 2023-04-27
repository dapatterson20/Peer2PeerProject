from flask import Flask, render_template
import os

app=Flask(__name__)

Index=-1

app.config['UPLOAD_FOLDER']='home/pemacs/Peer2PeerProject'

@app.route("/")
def index():
    global Index
    Index+=1
    imageList=os.listdir('static')
    if Index>=len(imageList):
        Index=0
    return render_template("index.html", user_image=imageList[Index])
