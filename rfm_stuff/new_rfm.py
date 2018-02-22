#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Antipin S.O. @RLDA

"""
    Подключение необходимых модулей
"""
import os
import sys

#import rfm69
import paho.mqtt.client as mqtt

import time

# DEBUG: dev_stuff
import random
import logging
from logging.handlers import TimedRotatingFileHandler

"""
    Подключение логера
"""

#path = "/home/pi/pyscripts/pylog/pylog.log"
path = "pylog.log"
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

rfh = TimedRotatingFileHandler(
                                path,
                                when="D",
                                interval=1,
                                backupCount=5)
rfh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
rfh.setFormatter(formatter)

log.addHandler(ch)
log.addHandler(rfh)

class RPI_hub(object):
    """
        Класс центрального хаба для устройств, в сущности просто объединение
        объектов rfm, mqtt_client. Включает в себя список инициализированных
        датчиков, для прохода и обновления данных в брокере.
    """
    def __init__(self, ip="192.168.0.56"):
        self.rfm = self.init_rfm()
        self.ip = ip
        self.mqtt_client = self.init_mqtt()
        self.snc_list = []

    def add_snc(self, snc):
        """
            Добавить объект класса Sencor в список
        """
        self.snc_list.append(snc)

    def init_rfm(self):
        """
            Инициализация RFM69
            На выходе объект класса rfm69
        """
        rfm_unit = "RFM zaglushka"
        # myconf = rfm69.RFM69Configuration()
        # rfm_unit = rfm69.RFM69(
        #                         dio0_pin=24,
        #                         reset_pin=22,
        #                         spi_channel=0,
        #                         config=myconf)
        # rfm_unit.set_rssi_threshold(-114)
        return rfm_unit

    def mqtt_on_connect(self, client, userdata, flags, rc):
        '''
            При подключении к порту брокера
        '''
        log.info("Connected to MQTT with rc: %s" % rc)

    def mqtt_on_disconnect(self, client, userdata, rc):
        '''
            При отключении от брокера
        '''
        if rc != 0:
            log.warn("Unexpected disconnection")
        else:
            log.info("Expected disconnection")

    def init_mqtt(self):
        """
            Функция инициализации клиента mqtt
            на выходе - объект класса mqtt.client
        """
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = self.mqtt_on_connect
        mqtt_client.on_disconnect = self.mqtt_on_disconnect

        mqtt_client.connect(self.ip, 1883, 60)
        mqtt_client.loop_start()
        return mqtt_client

    def loop(self):
        """
            Бесконечный цикл опроса
        """
        try:
            while True:
                self.read_real()
                self.snc_passage()
        except Exception as e:
            log.critical("Critical exc in loop")
            log.critical(str(e))
        except KeyboardInterrupt:
            log.info("That's all, folks")

    def read_real(self):
        """
            Метод чтения данных с rfm
        """
        # # Ожидание сообщения
        # inc_data = self.rfm.wait_for_packet(59)
        #
        # # Проверка данных (если данные не пришли type(inc_data!=None))
        # # если ответ пришел, данные записываются в кортеж
        # if type(inc_data) == tuple:
        #     # TEMP: Тестовая хренотень
        #     self.send_raw_data(inc_data)
        #     self.concat_data(inc_data)
        time.sleep(20)

    def snc_passage(self):
        """
            Проход по списку датчиков и перезапись значений в брокер
        """
        for snc in self.snc_list:
            if snc.is_fake:
                snc.data = snc.get_random_state()
            else:
                snc.check_timeout()
            snc.write2mqtt()


rpi_hub = RPI_hub()

class Sencor(object):
    def __init__(self, rpi_hub=rpi_hub):
        # Инициализация хаба из глобаьной области и
        self.rpi_hub = rpi_hub
        self.mqtt_c = self.rpi_hub.mqtt_client

        # таймаут ответа
        self.d_timeout = 0

        # время последнего ответа (*nix-style)
        self.last_responce = time.time()
        self.last_data = "-"

        # Полезные данные
        self.data = "Инициализация"
        self.rssi = 0
        self.bat_lvl = 0
        self.pack_id = 0

        self.topic_val = self.topic_com + "/val"
        self.topic_rssi = self.topic_com + "/rssi"
        self.topic_lstrsp = self.topic_com + "/lr"
        self.topic_bat = self.topic_com + "/bat"
        self.topic_packid = self.topic_com + "/packid"

    def check_timeout(self):
        '''
            Метод проверки timeout'а ответа
            если ответа не было дольше, чем timout сек,
            то устанавливает data = "timeout"
        '''
        __t_diff = time.time() - self.last_responce
        if __t_diff > self.d_timeout:
            self.data = "Таймаут"
            log.debug("Sencor: %s: time between responces: %s" % (
                    (str(type(self))+":"+self.addr), __t_diff))

    def write2mqtt(self):
        # Для отображения в OH2
        self.mqtt_c.publish(self.topic_val, self.data)

        # DEBUG: Для разработки
        self.mqtt_c.publish(self.topic_rssi, self.rssi)
        self.mqtt_c.publish(self.topic_bat, self.bat_lvl)
        self.mqtt_c.publish(self.topic_lstrsp, self.last_responce)
        self.mqtt_c.publish(self.topic_packid, self.pack_id)


class Air_t_snc(Sencor):
    ''' Класс датчиков температуры '''
    def __init__(self, addr, timeout=80, is_fake=True):
        self.addr = str(addr)
        self.topic_com = "oh/sncs/temp/air/" + self.addr
        self.d_timeout = timeout
        super(Air_t_snc, self).__init__()

        self.is_fake = is_fake
        self.snc_type = "SNC_T_AIR"
        self.type_id = 0
        self.data_err = 0x7FF
        self.rpi_hub.add_snc(self)

    def convert_data(self, data):
        self.last_responce = time.time()

        __data_lb = data[5]
        __data_sb = data[6] << 8

        __data_sum = (__data_lb & __data_sb) & 0xFFF

        if __data_sum == self.data_err:
            self.data = "Ошибка датчика"
        else:
            self.data = __data_sum

    def get_random_state(self):
        ''' Генератор псевдослучайных значений '''
        __limits = [19.00, 25.00]
        random_data = random.uniform(__limits[0], __limits[1])
        return random_data


if __name__ == '__main__':
    log.info("Entered main")
    fake_air_snc_1 = Air_t_snc(addr = 1)

    rpi_hub.loop()
