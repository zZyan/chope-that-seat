''' Script to subscribe and send email on specific contetent change
'''
import argparse
import time
import hashlib
from bs4 import BeautifulSoup
import smtplib
from selenium.webdriver.firefox.options import Options as FirefoxOptions

import logging

import re

from website_keywords import NOT_AVAILABLE_DIV_ID
from selenium import webdriver

def _seat_found_from_website(url) -> bool:
    ''' To check availability on supported website
    '''
    firefox_options = FirefoxOptions()
    firefox_options.add_argument('-headless')
    driver = webdriver.Firefox(options=firefox_options)
    driver.get(url)
    driver.implicitly_wait(10)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    for key, value in NOT_AVAILABLE_DIV_ID.items():
        if key in url:
            evidences = soup.find_all('div', value)
            return len(evidences) == 0

    logging.warning('URL not found in keywords dictionary')
    return False


def _write_message(url) -> str:
    email_subject = '[Chope Agent] Spotted. Chope Now.'
    email_body = f'Go to subsribed url: {url}'

    return f'Subject: {email_subject}\n\n{email_body}'


def _send_email(server, sender, email_address, message):
    try:
        server.sendmail(sender, email_address, message)
        logging.info('Email sent.')

    except Exception as error:
        logging.error('Error sending email: %s', error)


class ChopeAgent:
    ''' Manage subscribe, publish
    '''
    def __init__(self, email_address, password) -> None:
        self.__email_address = email_address
        self.__password = password
        # self.__server = smtplib.SMTP('smtp.gmail.com', 587)
        # self.__server = smtplib.SMTP('smtp.mail.yahoo.com', 587)

    def login(self) -> smtplib.SMTP:
        ''' Login email
        '''
        try:
            self.__server = smtplib.SMTP_SSL('smtp.mail.yahoo.com', 587)
            self.__server.starttls()
            self.__server.login(self.__email_address, self.__password)
        
        except Exception as error:
            logging.error('Error logging in for: %s, %s, %s', self.__email_address, self.__server,  error)
            self.__server.quit()

    def logout(self):
        ''' Logout
        '''
        self.__server.quit()
        

    def notify(self, user, *urls):
        ''' Notify on all urls 
        '''
        for url in urls:
            if _seat_found_from_website(url):
                message = _write_message(url)
                _send_email(self.__server, self.__email_address, user, message)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Webpage Monitor Script')

    parser.add_argument('-m', '--mail_address', type=str, required=True, help='email address of chope agent as sender')
    parser.add_argument('-p', '--mail_password', type=str, required=True, help='email password of chope agent as sender')
    parser.add_argument('-u', '--user', type=str, required=True, help='email address of user as subscriber')
    parser.add_argument('-l', '--links', type=str, nargs='+', required=True, help='links to subscribe to')

    args = parser.parse_args()

    # init a ChopeAgent
    agent = ChopeAgent(args.mail_address, args.mail_password)
    agent.login()
    agent.notify(args.user, args.links)
    agent.logout()


