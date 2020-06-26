# coding=utf-8

from bs4 import BeautifulSoup
import re,requests,time,datetime
from time import sleep 

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
	