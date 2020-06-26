# coding=utf-8

from threading import Thread
from time import sleep 
from utils import findPrice,is_number
from models import User,Sourcetype,Source,SourceUser
import config
from commands import bot

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
			sleep(config.update_interval)
		except:
			continue

thread = Thread(target = update_thread, args = (10, ))
#to enable cntrl+c break
thread.daemon = True
thread.start()
# thread.join()




bot.polling()