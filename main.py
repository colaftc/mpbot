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
from models import MPMessage, MPMessage_Pydantic, MPEvent, MPEvent_Pydantic
import hashlib, requests

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

API_URL = 'https://www.rechatun.com'
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

def get_user_info(openid : str):
    url = API_URL + '/api/mp-unionid/'
    res = requests.post(url, {
        'openid' : openid,
    })
    print(f'[获取推荐人信息] : {res.json()}')
    return res

def markup_agent(agent_uid : str, agent_unionid : str, customer_id: str, customer_unionid : str):
    url = API_URL + '/agent/promotion'
    res = requests.post(url, json={
        'agent_uid' : agent_uid,
        'agent_unionid' : agent_unionid,
        'customer_id' : customer_id,
        'customer_unionid' : customer_unionid,
        'lock' : False
    })
    print(f'[记录推荐行为] : {res.json()}')
    return res

class BaseReplyLoader:
    def __init__(self):
        self.replies = self._load()

    def _load(self):
        return [
            Reply('热茶屯是什么？', '热茶屯是茶行业新模式，品牌商直接发货，没有金字塔经销体系中间商，全国统一批发价'),
            # Reply('热茶屯安全吗？', '热茶屯保证您的资金安全，收益安全，货品质量安全，知识产权安全，税务法规安全'),
            Reply('人工客服', '在线客服功能维护中，请致电400-608-1929咨询'),
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

def check_agent(a, q):
    url = API_URL + '/api/check-agent/'
    res = requests.post(url, data={
        'a' : a,
        'q' : q,
    })
    print(f'[验证推广状态] : {res}')
    if res.status_code == 200:
        return res.json()
    return None

def openid_to_unionid(openid, extra=''):
    url = API_URL + '/wx/mp-unionid/'
    if extra != '':
        print(f'[带场景值转换unionid] : {extra}')
    res = requests.post(url, data={
        'openid' : openid,
        'extra' : extra,
    })
    print(f'[获取用户] : {res}')
    if res.status_code == 200:
        return res.json()
    return None


def tag_user(openid, tag_id=100):
    url = API_URL + '/wx/tag-user/'
    print(f'[新关注用户自动打标签] : {openid}')
    res = requests.get(API_URL + '/wx/tag-user/', data={
        'secret': 'ggadmin5197',
        'openid': openid,
        'tag_id': tag_id,
    })
    print(f'[用户打标结果] : {res}')
    if res.status_code == 200:
        return res.json()
    return None


def welcome_message(openid):
    d


async def _default_evt_handler(evt):
    print(f'[事件] : {evt}')
    print(f'[事件类型] : "{evt.event}"')
    e = await MPEvent.create(from_user=evt.source, evt=evt.event)
    if evt.event == 'subscribe_scan' or evt.event == 'subscribe':
        try:
            print(f'[未关注用户扫码关注事件] : 场景值"{evt.scene_id}"')
            e.extra = evt.scene_id
            print(e.extra)
            await e.save()
            params = evt.scene_id.split('&')
            params = list(map(lambda v: v[1], map(lambda v: v.split('='), params)))
            print(f'[SCENE_PARAM_PARSE] : {params}')
            agent = check_agent(params[0], params[1])

            if not agent:
                return False

            print(f'[推广者验证有效] : {agent["uid"]}')
            if agent['id'] == 5197:
                # 5197例外处理
                agent['openid'] = 'super-admin-agent'
                agent['unionid'] = 'super-admin-agent'
                print(f'[被推荐客户ID] : {evt.source}')

            # openid to unionid
            customer = openid_to_unionid(evt.source, evt.scene_id)


            print(f'[返回数据]{customer}')
            if customer.get('unionid', '') == '':
                raise Exception('无法获取unionid')

            print(f'[被推荐客户UNIONID] : {customer["unionid"]}')
            result = markup_agent(
                agent_uid=agent['uid'],
                agent_unionid=agent['unionid'],
                customer_id=0,
                customer_unionid=customer['unionid'],
            )
            print(f'[处理结果] : {result}')
        except:
            evt.scene_id = ''

        # tag user when subscribe
        tag_user_result = tag_user(evt.source)
        print(f'[打标返回数据]{tag_user_result}')
        return '欢迎您大驾光临热茶屯[玫瑰] ，热茶屯专业茶叶品牌批发 不卖单独消费者。\
        新模式 1.厂家直供就是便宜，从源头正规厂家直发茶店 2.分享式经济 介绍其他茶店到平台购买可获得永久反佣。\
        3.不定期大促活动 为茶店谋福利。    期待与您共同开拓未来[微笑]'


class MsgDispatcher:
    def __init__(self, loader: BaseReplyLoader, event_handler: callable = _default_evt_handler):
        self._loader = loader
        self._event_handler = event_handler

    async def dispatch(self, msg):
        if msg.type == 'text':
            # put msg in db
            await MPMessage.create(publisher=msg.source, content=msg.content)
            return self._loader.answer(msg.content)
        if msg.type == 'event':
            return await self._event_handler(msg)
        else:
            return self._loader.answer()

@app.get('/', response_class=PlainTextResponse)
async def wx_verify(
   signature: str,
   nonce: str,
   timestamp: str,
   echostr: str
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
    msg_signature: str,
    timestamp: str,
    nonce: str,
    request: Request,
):
    xml_body = await request.body()
    decrypted = crypto.decrypt_message(xml_body.decode(), msg_signature, timestamp, nonce)
    msg = parse_message(decrypted)

    dispatcher = MsgDispatcher(BaseReplyLoader())


    answer = await dispatcher.dispatch(msg)

    reply = create_reply(answer, message=msg, render=True)
    encrypted = crypto.encrypt_message(reply, nonce)
    return Response(encrypted, media_type='application/xml')

@app.get('/events/')
async def event_list(request : Request):
    openid = request.query_params.get('openid', '')
    evt = request.query_params.get('event', '')

    if not openid:
        if not evt:
            return await MPEvent.filter().order_by('-created_at')
        else:
            return await MPEvent.filter(evt=evt).order_by('-created_at')
    else:
        if not evt:
            return await MPEvent.filter(from_user=openid).order_by('-created_at')
        else:
            return await MPEvent.filter(from_user=openid).filter(evt=evt).order_by('-created_at')

# @app.post('/testing')
# async def testing(request : Request):
#     real_openid = 'o7OPz5NdjQFmShx_g2tcVAmlhZsU'
#     agent_openid = 'o7OPz5EdwMjpPlaw0IyNNNBaBd8g'
#     res = get_user_info(real_openid)
#     agent_res = get_user_info(agent_openid)
#     assert res.status_code == agent_res.status_code == 200
#     res = res.json()
#     agent_res = agent_res.json()
#     promo_res = markup_agent(agent_uid=agent_res['uid'], agent_unionid=agent_res['unionid'], customer_id=res['id'], customer_unionid=res['unionid'])
#     return promo_res.status_code
