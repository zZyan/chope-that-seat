''' Script to subscribe and send email on specific contetent change
'''
import argparse
import logging
import re
import sys
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlparse, parse_qs

import smtplib
import phonenumbers
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from twilio.rest import Client

from website_keywords import NOT_AVAILABLE_DIV_ID

def seat_found_from_website(url) -> bool:
    ''' To check availability on supported website
    '''
    parsed_url = urlparse(url)
    if not (parsed_url.scheme and parsed_url.netloc):
        return False

    firefox_options = FirefoxOptions()
    firefox_options.add_argument('-headless')
    driver = webdriver.Firefox(options=firefox_options)
    driver.get(url)
    driver.implicitly_wait(10)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    for key, value in NOT_AVAILABLE_DIV_ID.items():
        if key in url:
            evidences = soup.find_all('div', value)
            logging.info("NOT_AVAILABLE_DIV_ID found? %s", str())
            return len(evidences) == 0

    logging.warning('URL not found in keywords dictionary')
    return False


def _write_email(url) -> str:
    email_subject = '[Chope Agent] Spotted. Chope Now.'
    email_body = f'Go to subsribed url: {url}'

    return f'Subject: {email_subject}\n\n{email_body}'

def _write_message(url) -> str:
    # sanitize url
    parsed_url = urlparse(url)
    website_name = parsed_url.netloc.split('.')[0]

    # Extract endpoint
    endpoint = parsed_url.path.split("/")[-1]

    # Extract query parameters
    query_params = parse_qs(parsed_url.query)
    date = query_params["date"][0]
    seats = query_params["seats"][0]

    return f'''
Chop Agent: 
    proceed to site: {website_name.capitalize()}, to make reservation,
    {endpoint},
    date: {date},
    seat: {seats}
    '''

def _send_email(server, sender, email_address, message):
    try:
        server.sendmail(sender, email_address, message)
        logging.info('Email sent.')

    except Exception as error:
        logging.error('Error sending email: %s', error)

def _is_valid_email(value):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, value))

def _is_valid_number(value):
    pattern = r'^(\+?1[ -]?)?(\()?([2-9][0-8][0-9])(\))?([ -])?([2-9][0-9]{2})([ -])?([0-9]{4})$'
    return bool(re.match(pattern, value))

def _validate_args(values):
    if _is_valid_email(values.user):
        return _is_valid_email(values.agent)

    if _is_valid_number(values.user):
        return _is_valid_number(values.agent)

    return False

def _create_agent(values):
    if _is_valid_email(values.user):
        if not _is_valid_email(values.agent):
            return None
        return ChopeEmailAgent(values.agent, values.password)

    if _is_valid_number(values.user):
        if not _is_valid_number(values.agent):
            return None
        return ChopeMessengeAgent(values.agent,  values.id, values.password)

class ChopeEmailAgent:
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

    def on_available(self, user, *urls):
        ''' Notify on all urls 
        '''
        for url in urls:
            if seat_found_from_website(url):
                message = _write_email(url)
                self.notify(user, message)
    
    def notify(self, user, content):
        _send_email(self.__server, self.__email_address, user, content)


class ChopeMessengeAgent:
    '''Handles sending sms
    '''
    def __init__(self, agent, auth_id, auth_token) -> None:
        self.__client = Client(auth_id, auth_token)
        self.__agent = phonenumbers.format_number(phonenumbers.parse(agent, None), phonenumbers.PhoneNumberFormat.E164)
        print("agent created: ", self.__agent)
    
    def on_available(self, receiver, urls):
        print("check url: ", urls)

        for url in urls:
            print("check url: ", url)
            if seat_found_from_website(url):
                message_content = _write_message(url)
                self.notify(receiver, message_content)
            else:
                print("seat not found")

    def on_available_simple(self, receiver, url):
        if seat_found_from_website(url):
            message_content = _write_message(url)
            self.notify(receiver, message_content)
        else:
            print("seat not found")

    def notify(self, receiver, content):
        message = self.__client.messages.create(
            body=content,
            from_=self.__agent,
            to=(phonenumbers.format_number(phonenumbers.parse(receiver, None), phonenumbers.PhoneNumberFormat.E164)))
        print("message sent: ", message)


class ChopeAgent(ABC):
    ''' All agent types
    '''
    @abstractmethod
    def on_available(self, receiver, urls: List[str]):
        pass

    @abstractmethod
    def notify(self, receiver, content):
        pass


def test_send_message(agent, auth_id, auth_token, user):
    agent = ChopeMessengeAgent(agent, auth_id, auth_token)
    agent.notify(user, "sample text")

def test_on_available(agent, auth_id, auth_token, user, url):
    agent = ChopeMessengeAgent(agent, auth_id, auth_token)
    agent.on_available(user, url)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Webpage Monitor Script')

    parser.add_argument('-a', '--agent', type=str, required=True, help='email address or phone number of chope agent as sender')
    parser.add_argument('-i', '--id', type=str, required=False, help='sender id')
    parser.add_argument('-p', '--password', type=str, required=True, help='sender password of chope agent as sender')
    parser.add_argument('-u', '--user', type=str, required=True, help='email address of user as subscriber')
    parser.add_argument('-l', '--links', type=str, required=True, help='links separted by "," to subscribe to')

    args = parser.parse_args()
    if not _validate_args(args):
        logging.error("Invalid arguments for agent / sender")
        sys.exit()

    agent = _create_agent(args)
    links = args.links.split(",")
    agent.on_available(args.user, links)
