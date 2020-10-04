from fastapi import FastAPI, Body, Request
from fastapi.responses import PlainTextResponse
from environs import Env
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from wechatpy.utils import check_signature
from wechatpy import parse_message
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.crypto import WeChatCrypto
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

# initial crypto for mp message
crypto = WeChatCrypto(
    token=config['MP_SETTINGS']['TOKEN'],
    encoding_aes_key=config['MP_SETTINGS']['AESKEY'],
    app_id=config['MP_SETTINGS']['APPID'],
)

@app.get('/', response_class=PlainTextResponse)
async def wx_verify(
   signature : str,
   nonce : str,
   timestamp : str,
   echostr : str
):
    
    try:
        check_signature(config['MP_SETTINGS']['TOKEN'], signature, timestamp, nonce)
    except InvalidSignatureException:
        print('verify failed')
        return ''

    print([signature, nonce, timestamp, echostr])
    return echostr

@app.post('/')
async def reply_handler(
    msg_signature : str,
    timestamp : str,
    nonce : str,
    request : Request,
):
    xml_body = await request.body()
    decrypted = crypto.decrypt_message(xml_body.decode(), msg_signature, timestamp, nonce)
    msg = parse_message(decrypted)

    if msg.type == 'text':
        result = '收到文字消息'
    elif msg.type == 'image':
        result = '收到图片消息'
    else:
        result = '收到不支持的消息'

    return result