# -*- coding: utf-8 -*-
import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

def getXmlCdata(body):
    return ET.fromstring(str(body)).text

class BBSClient:
    def __init__(self, hostname: str, username: str, password: str, questionid: str = '0', answer: str = None, proxies: dict | None = None):
        self.session = requests.Session()
        self.hostname = hostname
        self.username = username
        self.password = password
        self.questionid = questionid
        self.answer = answer
        self._common_headers = {
            "Host": f"{hostname}",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,cn;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.proxies = proxies
        self.formhash = ''

    def login_form_hash(self):
        response = self.session.get(f'https://{self.hostname}/member.php?mod=logging&action=login').text
        loginhash = re.search(r'<div id="main_messaqge_(.+?)">', response).group(1)
        formhash = re.search(r'<input type="hidden" name="formhash" value="(.+?)" />', response).group(1)
        return loginhash, formhash

    def login(self):
        """Login with username and password"""
        loginhash, formhash = self.login_form_hash()
        login_url = f'https://{self.hostname}/member.php?mod=logging&action=login&loginsubmit=yes&loginhash={loginhash}&inajax=1'
        headers = {**self._common_headers, "origin": f'https://{self.hostname}', "referer": f'https://{self.hostname}/'}
        payload = {
            'formhash': formhash,
            'referer': f'https://{self.hostname}/',
            'username': self.username,
            'password': self.password,
            'questionid': self.questionid,
            'answer': self.answer,
        }

        response = self.session.post(login_url, proxies=self.proxies, data=payload, headers=headers)
        if response.status_code == 200:
            logger.info(f'Welcome {self.username}!')
            self.get_form_hash()
        else:
            raise ValueError('Verify Failed! Check your username and password!')

    def get_form_hash(self):
        response = self.session.get(f'https://{self.hostname}/home.php').text
        self.formhash = re.search(r'formhash=([\da-f]+)', response).group(1)

    def checkin(self):
        checkin_url = f'https://{self.hostname}/plugin.php?id=k_misign:sign&operation=qiandao&formhash={self.formhash}&inajax=1'
        return self.session.get(checkin_url).text

    def credit(self):
        credit_url = f"https://{self.hostname}/home.php?mod=spacecp&ac=credit&showcredit=1&inajax=1&ajaxtarget=extcreditmenu_menu"
        credit_response = self.session.get(credit_url).text

        # 解析 XML，提取 CDATA
        cdata_content = getXmlCdata(credit_response)

        # 使用 BeautifulSoup 解析 CDATA 内容
        cdata_soup = BeautifulSoup(cdata_content, features="lxml")
        credits = cdata_soup.select('ul li')
        hcredits = '\n'.join(hcredit.text for hcredit in credits)
        return hcredits

    def invite(self):
        return self.session.get(f'https://{self.hostname}/?fromuid={os.environ.get("UID")}')

    def logout(self):
        return getXmlCdata(self.session.get(f'https://{self.hostname}/member.php?mod=logging&action=logout&formhash={self.formhash}&inajax=1').text)


if __name__ == '__main__':
    try:
        url = 'https://' + os.environ.get('HOSTNAME')
        logger.info(url)
        client = BBSClient(urlparse(url).hostname, os.environ.get('USERNAME'), os.environ.get('PASSWORD'))
        result = client.invite()
        logger.info(result.url)
        client.login()
        result = client.checkin()
        logger.info(result)
        credit = client.credit()
        logger.info(f'{client.username}有\n{credit}')
        logger.info(client.logout())
    except Exception as e:
        logger.error(e)
        sys.exit(1)
