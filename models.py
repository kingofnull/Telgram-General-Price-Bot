from peewee import *

#--Model definitions--
db = SqliteDatabase('db.sqlite')

class BaseModel(Model):
	class Meta:
		database = db

class User(BaseModel):
    username = CharField(unique=True,null=True,max_length=128)
    chat_id = CharField(unique=True,max_length=128)

class Sourcetype(BaseModel):
	title = CharField(max_length=128)
	url = TextField()

class Source(BaseModel):
	url = TextField()
	last_value = DecimalField(default=0)
	type = ForeignKeyField(Sourcetype,null=True)

class SourceUser(BaseModel):
	# id=AutoField()
	name = CharField(max_length=128,null=True)
	source = ForeignKeyField(Source)
	user = ForeignKeyField(User)
	change_threshold=FloatField(null=True)
	change_threshold_unit_type=IntegerField(null=True)
	# class Meta:
		# primary_key = CompositeKey('source', 'user')
		
#--End of Model Definitions--


db.connect()
db.create_tables([User,Sourcetype,Source,SourceUser])
