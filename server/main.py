#!/usr/bin/env python

import logging
import os
import uuid
import shlex
import subprocess
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.process
from tornado.options import options
from tornado.options import define
from tornado.log import enable_pretty_logging

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        ROOT = os.path.dirname(os.path.abspath(__file__))
        path = lambda root,*a: os.path.join(root, *a)
        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            static_path=path(ROOT, 'static'),
            static_handler_args=dict(default_filename="index.html"),
            xsrf_cookies=False,
            autoescape=None,
            serve_traceback=True
        )

        handlers = [
            (r"/run", AlignHandler),
            (r"/(.*)", tornado.web.StaticFileHandler, {'path': settings["static_path"], 'default_filename' : 'index.html'}),
        ]
        tornado.web.Application.__init__(self, handlers, **settings)

class AlignHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.upload_id = str(uuid.uuid4())
        current_directory = os.path.dirname(os.path.abspath(__file__))
        parent_directory = os.path.join(current_directory, os.pardir)
        self.aligner_directory = parent_directory + "/aligner/" 


    async def post(self, *args, **kwargs):
        logging.info("Got alignment request")
        if ("wav" not in self.request.files):
            raise tornado.web.HTTPError(status_code=400, reason="'wav' file not provided in the upload")
        if ("txt" not in self.request.files):
            raise tornado.web.HTTPError(status_code=400, reason="'txt' file not provided in the upload")

        wav_file = self.request.files['wav'][0]
        wav_filename = wav_file['filename']
        wav_extension = os.path.splitext(wav_filename)[1]
        wav_basename = os.path.splitext(wav_filename)[0]
        
        upload_wav_filename = "user_files/" + self.upload_id + ".wav" 
        output_wav_file = open(self.aligner_directory + upload_wav_filename, 'wb')
        output_wav_file.write(wav_file['body'])
        output_wav_file.close()

        txt_file = self.request.files['txt'][0]
        upload_txt_filename =  "user_files/" + self.upload_id + ".txt" 
        output_txt_file = open(self.aligner_directory + upload_txt_filename, 'wb')
        output_txt_file.write(txt_file['body'])
        output_txt_file.close()

        return_textgrid_filename = "user_files/" + self.upload_id + ".TextGrid"
        logging.info("Starting alignment process")
        await run_align(self.aligner_directory, upload_wav_filename, upload_txt_filename, return_textgrid_filename)
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=%s' % wav_basename + ".TextGrid")
        self.render(self.aligner_directory + "user_files/" + self.upload_id + ".TextGrid")
        logging.info("Finished alignment request")
    
    def on_finish(self):
        logging.info("Cleaning up")
        for extension in ["wav", "txt", "TextGrid"]:
            try:
                filename = self.aligner_directory + "user_files/" + self.upload_id + "." + extension
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception as e:
                logging.exception("Error occurred when cleaning up")

async def run_align(aligner_directory, wav, txt, textgrid):
    logging.info("Initializing alignment process")
    tornado.process.Subprocess.initialize()
    cmd = "./align.sh %s %s %s" % (wav, txt, textgrid)    
    logging.info("Running command: %s" % cmd)
    proc = tornado.process.Subprocess(shlex.split(cmd), stdout=tornado.process.Subprocess.STREAM, stderr=subprocess.STDOUT, cwd=aligner_directory)
    ret = await proc.wait_for_exit(raise_error=False)
    if ret == 0:
        return
    else:
        output = (await proc.stdout.read_until_close()).decode("utf-8") 
        logging.warn("Alignment failed. Last 100 chars of output: " + str(output)[-100:])
        raise Exception(output)


def main():
    #logging.basicConfig(level=logging.DEBUG, format="%(levelname)8s %(asctime)s %(message)s ")
    enable_pretty_logging()

    logging.debug('Starting up server')

    define("certfile", default="", help="certificate file for secured SSL connection")
    define("keyfile", default="", help="key file for secured SSL connection")

    tornado.options.parse_command_line()
    app = Application()
    if options.certfile and options.keyfile:
        ssl_options = {
          "certfile": options.certfile,
          "keyfile": options.keyfile,
        }
        logging.info("Using SSL for serving requests")
        app.listen(options.port, ssl_options=ssl_options)
    else:
        app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()