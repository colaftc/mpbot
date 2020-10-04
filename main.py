from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from wechatpy import WeChatClient
import hashlib

app = FastAPI()

config = {
    'MP' : {
        'TOKEN' : 'gzgg486180401',
        'EncodingAESKey' : 'Jyf2plzPp3BNC5B55o0dXb10nY2qmb58QplUt8a9vRn',
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