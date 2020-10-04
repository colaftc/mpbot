from fastapi import FastAPI
from environs import Env
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from wechatpy import WeChatClient
import hashlib

app = FastAPI()

# load the .env file, if exists
env = Env()
env.read_env()

config = {
    'MP_SETTINGS' : {
        'TOKEN' : env.str('MPBOT_TOKEN'),
        'AESKEY' : env.str('MPBOT_ENCODING_AESKEY'),
        'APPID' : env.str('MPBOT_APPID'),
        'SECRET' : env.str('MPBOT_SECRET'),
    },
}

origins = [
    '*',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/wx-verify')
async def wx_verify(
   signature : str,
   nonce : str,
   timestamp : str,
   echostr : str
):
    return {'echostr' : echostr}