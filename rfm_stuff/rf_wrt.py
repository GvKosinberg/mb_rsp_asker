import rfm69
import logging
import time

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("testo")


s = 0
def init_rfm():
    myconf = rfm69.RFM69Configuration()
    rfm_unit = rfm69.RFM69(
                            dio0_pin=24,
                            reset_pin=22,
                            spi_channel=0,
                            config=myconf)
    # setting RSSI treshold
    rfm_unit.set_rssi_threshold(-114)
    #rfm_unit.config.packet_config_1.variable_length = False
    return rfm_unit

def write_true(i, n):
    pack = [210, 0, 14, 0, 0]
    pack[4] = i
    pack[3] = n
    # pack[0] = 210
    # pack[1] =
    rfm.send_packet(pack)

def wait_4_responce(rfm):
    rfm.wait_for_packet(10)

if __name__ == '__main__':
    rfm = init_rfm()
    msg = 0
    inc = 0
    try:
        while True:
            log.debug("##############################################")
            write_true(msg, inc)
            wait_4_responce(rfm)
            msg = 1 if msg == 0 else 0
            inc += 1

            #time.sleep(10)
    except KeyboardInterrupt:
        print("That's all, folks")
