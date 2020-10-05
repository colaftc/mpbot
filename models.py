from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

class MPMessage(models.Model):
    id = fields.IntField(pk=True)
    # publisher record the union_id of wechat user, not nickname
    publisher = fields.CharField(max_length=30)
    content = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

# pydantic model
MPMessage_Pydantic = pydantic_model_creator(MPMessage, name='MPMessage')