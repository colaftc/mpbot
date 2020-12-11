from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

class MPEvent(models.Model):
    id = fields.IntField(pk=True)
    from_user = fields.CharField(max_length=200)
    evt = fields.CharField(max_length=100)
    extra = fields.CharField(max_length=200, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

class MPMessage(models.Model):
    id = fields.IntField(pk=True)
    # publisher record the union_id of wechat user, not nickname
    publisher = fields.CharField(max_length=30)
    content = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

# pydantic model
MPMessage_Pydantic = pydantic_model_creator(MPMessage, name='MPMessage')
MPEvent_Pydantic = pydantic_model_creator(MPEvent, name='MPEvent')