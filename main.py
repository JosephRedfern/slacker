from flask import Flask, jsonify, request
from threading import Thread
from subprocess import call
import pickle
import tempfile
import os.path
import os
import requests
import urllib
import random

COOKIES = {'wordseye': 'wordseye_cookie_goes_here'}
URL = "https://www.wordseye.com/workspace?api=t&depict=t&ptext={scene}"
GIF_PATH = "PATH_TO_FOLDER_TO_STORE_GIFS"
GIF_URL = "URL_TO_GIF_FOLDER_WITH_PLACEHOLDER_SOMEWHERE" # i.e. https://interwobble.site/gifs/{0}"
PICKLE_FILENAME = "images.pickle"

app = Flask(__name__)

custom = {}
if os.path.isfile(PICKLE_FILENAME):
    print("loading custom image db")
    with open(PICKLE_FILENAME, 'rb') as handle:
        custom = pickle.load(handle)

@app.route('/get')
def get():
    scene = request.args.get('text')
    response_url = request.args.get('response_url')

    # TODO: make this nicer?
    if scene.startswith('add'):
        process_add(scene, response_url)
    elif scene.startswith('reversed'):
        Thread(target=reverse_gif, kwargs={'response_url': response_url, 'string': scene}).start()
    elif scene.startswith('rewound'):
        Thread(target=rewind_gif, kwargs={'response_url': response_url, 'string': scene}).start()
    elif scene.strip().lower() in custom:
        message = {
            "response_type": "in_channel",
            "text": scene,
            "attachments": [{
                'title': scene,
                'image_url': random.choice(custom[scene.strip().lower()])
            }]}
        return jsonify(message)
    else:
        # WordsEye can take a while to respond, so respond with blank message (as per API docs)
        Thread(target=process_request, kwargs={'response_url': response_url, 'scene': scene}).start()

    return jsonify({"response_type": "in_channel"})

def reverse_gif(string, response_url):
    _, gif_path = tempfile.mkstemp()
    fid, reversed_gif_path = tempfile.mkstemp(prefix=GIF_PATH, suffix=".gif")
    gif_url = string.split()[-1]

    urllib.urlretrieve(gif_url, gif_path)

    with os.fdopen(fid, 'w') as f:
        ret = call(["gifsicle", gif_path, "#-1-0"], stdout=f)
        os.chmod(reversed_gif_path, 444)

    gif_name = reversed_gif_path.split("/")[-1]

    path = GIF_PATH.format(gif_name)

    message = {
            "response_type": "in_channel",
            "text": "Reversed!",
            "attachments": [{
                'title': "Reversed Gif:",
                'image_url': path,
            }]
        }

    requests.post(response_url, json=message)


# this should probably be merged with reverse_gif, with an additional flag (or similar) to avoid duplication
def rewind_gif(string, response_url):
    _, gif_path = tempfile.mkstemp()
    fid, reversed_gif_path = tempfile.mkstemp(prefix=GIF_PATH, suffix=".gif")
    fid2 , rewind_gif_path = tempfile.mkstemp(prefix=GIF_PATH, suffix=".gif")

    gif_url = string.split()[-1]

    urllib.urlretrieve(gif_url, gif_path)

    with os.fdopen(fid, 'w') as f:
	#This can almost certainly be done with one call to gifsicle.
        ret = call(["gifsicle", gif_path, "#-1-0"], stdout=f)
        os.chmod(reversed_gif_path, 444) #this is nasty
        with os.fdopen(fid2, 'w') as f2:
            call(["gifsicle", reversed_gif_path, gif_path], stdout=f2)
            os.chmod(rewind_gif_path, 444)

    gif_name = rewind_gif_path.split("/")[-1]

    path = GIF_PATH.format(gif_name)

    message = {
            "response_type": "in_channel",
            "text": "Reversed!",
            "attachments": [{
                'title': "Reversed Gif:",
                'image_url': path,
            }]
        }

    requests.post(response_url, json=message)

def process_add(string, response_url):
    term = ' '.join(string.split(' ')[1:-1])
    url = string.split(' ')[-1]

    if term.lower().strip() not in custom:
        custom[term.lower().strip()] = [url]
    else:
        custom[term.lower().strip()].append(url)

    with open(PICKLE_FILENAME, 'wb') as handle:
        pickle.dump(custom, handle)

    message = {
            "response_type": "in_channel",
            "text": "{0} added as a custom image".format(term.lower().strip()),
            "attachments": [{
                'title': term.lower().strip(),
                'image_url': url
            }]
        }

    requests.post(response_url, json=message)


def process_request(response_url, scene):
    r = requests.get(URL.format(scene=scene), cookies=COOKIES).json()
    print("Got scene image URL, sending to channel ({0})".format(r['url']))

    message = {
            "response_type": "in_channel",
            "text": scene,
            "attachments": [{
                'title': scene,
                'image_url': r['url']
            }]
        }

    requests.post(response_url, json=message)
    print("Sent.")

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
