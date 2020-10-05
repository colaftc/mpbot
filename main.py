# pylint: disable=E0611

from fastapi import FastAPI, Body, Request
from fastapi.responses import PlainTextResponse, Response
from environs import Env
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
from wechatpy import parse_message
from wechatpy.utils import check_signature
from wechatpy.replies import TextReply, create_reply
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.crypto import WeChatCrypto
from collections import namedtuple
from functools import reduce
from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise
from models import MPMessage, MPMessage_Pydantic
import hashlib

# load the .env file, if exists
env = Env()
env.read_env()

config : Dict[str, any] = {
    'MP_SETTINGS' : {
        'TOKEN' : env.str('MPBOT_TOKEN'),
        'AESKEY' : env.str('MPBOT_ENCODING_AESKEY'),
        'APPID' : env.str('MPBOT_APPID'),
        'SECRET' : env.str('MPBOT_SECRET'),
        'DB' : env.str('MPBOT_DB_URI'),
    },
}

app = FastAPI(title='Wechat MP platform message auto replier')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

register_tortoise(
    app,
    db_url=config['MP_SETTINGS']['DB'],
    # create table
    generate_schemas=True,
    add_exception_handlers=True,
    modules={'models' : ['models', ]},
)

# initial crypto for mp message
crypto = WeChatCrypto(
    token=config['MP_SETTINGS']['TOKEN'],
    encoding_aes_key=config['MP_SETTINGS']['AESKEY'],
    app_id=config['MP_SETTINGS']['APPID'],
)

Reply = namedtuple('Reply', ['question', 'answer'])

class BaseReplyLoader:
    def __init__(self):
        self.replies = self._load()

    def _load(self):
        return [
            Reply('热茶屯是什么？', '热茶屯是茶行业新模式，品牌商直接发货，没有金字塔经销体系中间商，全国统一批发价'),
            Reply('热茶屯安全吗？', '热茶屯保证您的资金安全，收益安全，货品质量安全，知识产权安全，税务法规安全'),
            Reply('人工客服', '在线客服功能维护中，请致电400-688-6888咨询'),
        ]

    def get_question_list(self):
        return [r.question for r in self.replies]

    def default_reply(self, sep : str = '\n'):
        answer = reduce(lambda c, n : f'{c}{sep}{n}', self.get_question_list())
        return f'小屯暂不支持此类消息喔，请使用数字或文字咨询{sep}{answer}'

    def answer(self, question : str):
        result = [r for r in self.replies if r.question == question]
        if len(result) == 1:
            return result[0].answer
        return self.default_reply()

class MsgDispatcher:
    def __init__(self, loader : BaseReplyLoader):
        self._loader = loader

    def dispatch(self, msg):
        if msg.type == 'text':
            return self._loader.answer(msg.content)
        else:
            return self._loader.answer()

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

    # put msg in db
    MPMessage.create(publisher=msg.source, content=msg.content)

    dispatcher = MsgDispatcher(BaseReplyLoader())
    answer = dispatcher.dispatch(msg)

    reply = create_reply(answer, message=msg, render=True)
    encrypted = crypto.encrypt_message(reply, nonce)
    return Response(encrypted, media_type='application/xml')