import datetime
import smtplib
import ssl
from types import prepare_class
from selenium import webdriver
import time
import json

class Booking:
    PATH = "C:\Program Files (x86)\chromedriver.exe"

    def __init__(self):
        self.driver = None

    @staticmethod
    def read_info():
        with open("info.json") as f:
            return json.load(f)


    def get_cred(self):
        with open("credentials.txt") as f:
            for row in f:
                if "email" in row:
                    SENDER = row.split(':')[1].strip()
                elif "password" in row:
                    PASSWORD = row.split(':')[1].strip()
        return SENDER, PASSWORD


    def send_mail(self, receivers, message):
        assert isinstance(receivers, list), "receivers must be of type list"

        # port = 587
        ssl_port = 465
        SENDER, PASSWORD = self.get_cred()

        context = ssl.create_default_context()
        host = "smtp.gmail.com"
        # with smtplib.SMTP('localhost', 1025) as smtp:
        with smtplib.SMTP_SSL(host, ssl_port, context=context) as smtp:
            smtp.login(SENDER, PASSWORD)

            for receiver in receivers:
                smtp.sendmail(SENDER, receiver, message.encode())


    def check_drivein(self):
        self.driver = webdriver.Chrome(self.PATH)
        self.driver.get(r"https://notkarnandrivein.se/")
        time.sleep(1)
        tider_id = self.driver.find_element_by_id("tider")
        info = self.read_info()
        slots_available = info['drivein']['slots_available']
        
        scraped_free_slots = tider_id.text != "INGA LEDIGA TIDER ATT BOKA JUST NU"
        if scraped_free_slots and slots_available == False:
            # New slots have been released
            found_new_slots = True
        else:
            found_new_slots = False
        self.driver.quit()
        return found_new_slots, scraped_free_slots

    def check_vgregion(self):
        self.driver = webdriver.Chrome(self.PATH)
        self.driver.get(r"https://www.vgregion.se/ov/vaccinationstider/bokningsbara-tider/")
        time.sleep(1)
        table = self.driver.find_element_by_class_name("list-component")
        records = table.find_element_by_class_name("block__row")

        h3 = records.find_elements_by_tag_name("h3")
        a = records.find_elements_by_tag_name("a")

        info = self.read_info()
        slots = info['vgregion']['slots']
        slots_scraped = {k.text: v.get_attribute("href") for k, v in zip(h3, a)}
        new_slots = {}
        for place, link in slots_scraped.items():
            if place not in slots.keys():
                new_slots.update({place: link})

        self.driver.quit()
        return new_slots, slots_scraped


    def run(self, receivers):

        # Check if script is allowed to run at current time
        info = self.read_info()
        now = datetime.datetime.now()
        for times in info['skip_time']:
            h1, m1, h2, m2 = times
            t1 = datetime.time(h1, m1)
            t2 = datetime.time(h2, m2)
            if t1 > now.time() and t2 < now.time():
                # In skip time
                return None
        
        # Check drive-in
        drivein_new, drivein_slots_available = self.check_drivein()
        time.sleep(1)

        # Check vgregion
        vgr_new, vgr_scraped = self.check_vgregion()

        info['drivein']['slots_available'] = drivein_slots_available
        info['vgregion']['slots'] = vgr_scraped
        info['last_check'] = now.strftime("%Y-%m-%d %H:%M")
        with open('info.json', "w") as f:
            json.dump(info, f, indent=4)

        message = u"Subject: New vaccine slots available\n\n"
        send = False
        if drivein_new:
            send = True
            message += u"New drivein slots available in Slottsskogen\n"
            message += u"https://notkarnandrivein.se/\n\n\n"
        if vgr_new:
            send = True
            for k, v in vgr_scraped.items():
                message += u"{}\n".format(k)
                message += u"{}\n\n".format(v)
        
        message += u"Mvh\nAutoFrallan"

        print(message)

        if send:
            self.send_mail(receivers, message)
        return message

book = Booking()
receivers = ['autofrallan@gmail.com']
msg = book.run(receivers)