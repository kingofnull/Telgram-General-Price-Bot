# coding=utf-8
from time import sleep
import decimal
from models import User,Sourcetype,Source,SourceUser
import telebot
from telebot import types
import config

# set proxy for telebot api
# telebot.apihelper.proxy = config.proxy

bot = telebot.TeleBot(config.bot_token)

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
