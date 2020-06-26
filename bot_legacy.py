# coding=utf-8

import telebot
from telebot import types
from threading import Thread
from time import sleep
from peewee import *
import datetime
from bs4 import BeautifulSoup
import decimal
import re
import requests
import time
from requests.models import PreparedRequest



def findPrice(url):
	userAgent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36"
	try:
		r=requests.get(url, params={'_t':time.time()},headers={'pragma': 'no-cache','cache-control': 'no-cache','User-Agent': userAgent})
		html = r.text
	except:
		return None
		
	soup = BeautifulSoup(html, "lxml")
	priceNode=soup.find("meta",  property="product:price:amount")
	if priceNode is None:
		priceNode=soup.find(itemprop="price")
		if priceNode is None:
			m=re.search("\"price\"\s*\:\s*\"([\d\.]+)\"", html, re.MULTILINE)

			if m is None:
				return None
			else:
				print("price found on `\"price\":\"\"")
				price=m.group(1)
				
		else:
			print("price found on `itemprop=price`")
			price=priceNode.get_text()
			
	else:
		print("price found on `product:price:amount`")
		price = priceNode["content"]
	
	price = re.sub('[\$,]', '', price)
	return decimal.Decimal(price)


def is_number(n):
    try:
        float(n)   # Type-casting the string to `float`.
                   # If string is not a valid `float`, 
                   # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True
	

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


def update_thread(arg):
	while 1:
		try:
			for s in Source.select().join(SourceUser).distinct():
				print("checking source of #{} . . .".format(s.id))
				price=findPrice(s.url)
				
				if price is None:
					print("gettting price failed!!!")
					continue
					
				print("Current price: {:,.2f}".format(price))
				
				if price != s.last_value:
					price=abs(price)
					lastPrice=s.last_value
					s.last_value=price
					s.save()
					# Source.update(last_value=price).where(Source.id == s.id).execute()
					for u in User.select(User.chat_id,SourceUser.name,SourceUser.change_threshold,SourceUser.change_threshold_unit_type).join(SourceUser).where(SourceUser.source==s):
						if 	(
								(u.sourceuser.change_threshold_unit_type==1) 
								and 
								(u.sourceuser.change_threshold <= abs(price-lastPrice))
							) or (
								(u.sourceuser.change_threshold_unit_type==2)
								and
								(lastPrice*u.sourceuser.change_threshold*0.01 <= abs(price-lastPrice))
							):
								print("new change detected for user #{} !!! New Price: {:,.2f} Change: ({:+,.2f})".format(u.chat_id,price,price-lastPrice))
								text="The item’s \"{}\"  price has changed.\n New Price:\t `{:,.2f}` \n Change:\t `({:+,.2f})`".format(u.sourceuser.name.encode('utf-8'),price,price-lastPrice)
								msg = bot.send_message(u.chat_id,text,parse_mode="Markdown")

		
			print("sleeping ...")
			sleep(10)
		except:
			continue



		


thread = Thread(target = update_thread, args = (10, ))
#to enable cntrl+c break
thread.daemon = True
thread.start()
# thread.join()

# set proxy for telebot api
# telebot.apihelper.proxy = {'https':'http://127.0.0.1:9050'}

bot = telebot.TeleBot("646954413:AAFArbfs8jnII3e64PsVhmC06-t0pL5yhnI")

cancelMarkup = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancelMarkup.row(types.KeyboardButton('Cancel'))

listMarkup = types.ReplyKeyboardMarkup(resize_keyboard=True)
listMarkup.row(types.KeyboardButton('List'),types.KeyboardButton('Add'))



#--Command handlers--
def showSourceList(chat_id,message_id=None):
	try:
		text="This it the list: \n"
		markup = types.InlineKeyboardMarkup()
		changeTypeMap={1:'$$$',2:'%%%'}
		sourceUserList=SourceUser.select(User.chat_id,SourceUser.name,SourceUser.change_threshold,SourceUser.change_threshold_unit_type,Source.last_value,SourceUser.id).join(User).switch(SourceUser).join(Source).where(User.chat_id==chat_id)
		if not sourceUserList:
			text='You don\'t have any source!!! '
		else:
			for su in sourceUserList:
				markup.row(types.InlineKeyboardButton("Name: {} \n Change Type: {} \n Change Value: {} \n Current Price: {:,.2f}".format(su.name.encode('utf-8'),changeTypeMap[su.change_threshold_unit_type],su.change_threshold,su.source.last_value), callback_data="edit_"+str(su.id)))
		
		if message_id is None:
			bot.send_message(chat_id,text,reply_markup=markup)
		else:
			bot.edit_message_text(text,chat_id,message_id,reply_markup=markup)
	except:
			pass
	
#Handles all messages for which the lambda returns True
@bot.callback_query_handler(func=lambda query: "back"==query.data)
def backHandler(query):
	showSourceList(query.message.json['chat']['id'],query.message.json['message_id'])

@bot.message_handler(func=lambda message: message.text.lower() == 'list')
def listHandler(m):
	showSourceList(m.chat.id)
	
@bot.message_handler(func=lambda message: message.text.lower() == 'cancel')
def cancelHandler(m):
	bot.send_message(m.chat.id, "Ok Bye!!!",reply_markup=listMarkup)
	
@bot.callback_query_handler(func=lambda query: re.match("^edit_(\d+)$", query.data))
def  editSourceCallback(query):
	try:
		m=re.match("^edit_(\d+)$", query.data)
		# bot.edit_message_text('4',message.chat.id,sent.message_id)
		source_user_id=m.group(1)
		sourceData=SourceUser.select(User.chat_id,SourceUser.name,SourceUser.change_threshold,SourceUser.change_threshold_unit_type,Source.last_value,SourceUser.id).join(User).switch(SourceUser).join(Source).where(SourceUser.id==source_user_id).first();
		markup = types.InlineKeyboardMarkup()
		markup.row(types.InlineKeyboardButton("Delete", callback_data="delete_"+str(source_user_id)))
		# markup.row(types.InlineKeyboardButton("Reconfig", callback_data="reconfig_"+str(source_user_id)))
		markup.row(types.InlineKeyboardButton("Back", callback_data="back"))
		bot.edit_message_text('What do you want to do with "{}"?'.format(sourceData.name.encode('utf-8')),query.message.json['chat']['id'],query.message.json['message_id'],reply_markup=markup)
	except:
			pass
	
@bot.callback_query_handler(func=lambda query: re.match("^delete_(\d+)$", query.data))
def  deleteCallback(query):
	try:
		m=re.match("^delete_(\d+)$", query.data)
		source_user_id=m.group(1)
		sourceData=SourceUser.select().join(User).switch(SourceUser).join(Source).where(SourceUser.id==source_user_id,User.chat_id==query.message.json['chat']['id']).first();
		sourceData.delete_instance()
		
		bot.edit_message_text('Source has been deleted!!!',query.message.json['chat']['id'],query.message.json['message_id'])

		sleep(3)
		
		showSourceList(query.message.json['chat']['id'],query.message.json['message_id'])
	except:
			pass
	
@bot.message_handler(func=lambda message: message.text.lower() == 'add')
@bot.message_handler(commands=['add','start'])
def add(m):
	try:

		msg = bot.send_message(m.chat.id, "Send me your url:",reply_markup=cancelMarkup)
		def getUrl(m):
			bot.send_chat_action(m.chat.id, 'typing')
			try:
				if m.text.lower()=='cancel':
					bot.send_message(m.chat.id, "Ok Bye!!!",reply_markup=listMarkup)
					return
				url=m.text
				
				try:
					price=findPrice(url)
				except:
					price=None
				if price is None:
					msg = bot.send_message(m.chat.id, "Sorry,I cant find the price, Try again:",reply_markup=cancelMarkup)
					bot.register_next_step_handler(msg, getUrl)
					return
				
				
				msg = bot.send_message(m.chat.id, "I found the price: "+"{:,}".format(price))
				
				user, created = User.get_or_create(
					username=m.chat.username,
					chat_id=m.chat.id
				)
				
				source, created = Source.get_or_create(
					url=url,
				)
				
				
				msg = bot.send_message(m.chat.id, "Enter a name for source:",reply_markup=cancelMarkup)
				def nameHandler(m):
					try:
						if m.text.lower()=='cancel':
							bot.send_message(m.chat.id, "Ok Bye!!!",reply_markup=listMarkup)
							return
						name=m.text
						markup = types.ReplyKeyboardMarkup(row_width=2,resize_keyboard=True)
						markup.add(types.KeyboardButton('$'),types.KeyboardButton('%'),types.KeyboardButton('Cancel'))
						
						msg = bot.send_message(m.chat.id, "Choose your change unit",reply_markup=markup)
						
						def unitTypeHandler(m):
							try:
								if m.text.lower()=='cancel':
									bot.send_message(m.chat.id, "Ok Bye!!!",reply_markup=listMarkup)
									return
								changeTypeMap={'$':1,'%':2}
								if m.text not in changeTypeMap:
									msg = bot.send_message(m.chat.id, "Invalid change unit, Try again:",reply_markup=markup)
									bot.register_next_step_handler(msg, sourceTypeHandler)
									return
									
								changeType=changeTypeMap[m.text];
								msg = bot.send_message(m.chat.id, "Enter change value:",reply_markup=cancelMarkup)
								
								def chageValueHandler(m):
									try:
										if m.text.lower()=='cancel':
											bot.send_message(m.chat.id, "Ok Bye!!!",reply_markup=listMarkup)
											return
										changeValue = m.text
										changeValue = re.sub('[\$,]', '', changeValue)
										if not is_number(changeValue):
											msg = bot.send_message(m.chat.id, "Entered value is not valid. Try again:",reply_markup=cancelMarkup)
											bot.register_next_step_handler(msg, chageValueHandler)
											return
											
										changeValue = decimal.Decimal(changeValue)
										
										sourceUser, created = SourceUser.get_or_create(
											source = source,
											user= user,
										)
										sourceUser.name= name
										sourceUser.change_threshold=changeValue
										sourceUser.change_threshold_unit_type=changeType
										sourceUser.save()
										
										if created :
											msg = bot.send_message(m.chat.id, "Your source has been added successfully!!!",reply_markup=listMarkup)
										else:
											msg = bot.send_message(m.chat.id, "Your source has been updated  successfully!!!",reply_markup=listMarkup)
						
										
									except:
										msg = bot.send_message(m.chat.id, "sorry , I can not handle your request!!!")

								bot.register_next_step_handler(msg, chageValueHandler)
							
							except:
								msg = bot.send_message(m.chat.id, "sorry , I can not handle your request!!!",reply_markup=listMarkup)

						bot.register_next_step_handler(msg, unitTypeHandler)
					
					except:
						msg = bot.send_message(m.chat.id, "sorry , I can not handle your request!!!",reply_markup=listMarkup)
	
				bot.register_next_step_handler(msg, nameHandler)
				
			except:
				msg = bot.send_message(m.chat.id, "sorry , I can not handle your request!!!",reply_markup=listMarkup)
	
			

			
		bot.register_next_step_handler(msg, getUrl)
	except:
		msg = bot.send_message(m.chat.id, "sorry , I can not handle your request!!!",reply_markup=listMarkup)
	
#--End of command handlers--

bot.polling()