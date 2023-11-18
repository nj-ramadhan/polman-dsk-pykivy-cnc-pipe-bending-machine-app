import paho.mqtt.publish as publish
import time

# msgs = [{'topic':"data_out/test", 'payload':200},
#         ("paho/test/multiple", "multiple 2", 0, False)]
# publish.multiple("data_out/test", 201, hostname="broker.hivemq.com", port=1883)

n = 1
good = 1
not_good = 1

while(good < 100):
    msgs = [{'topic':"data_out/test", 'payload':good},
        {'topic':"data_out2/test", 'payload':not_good},]

    publish.multiple(msgs, hostname="broker.hivemq.com", port=1883)
    print("n:" + str(n))
    time.sleep(0.5)

    n+=1
    good+=1
    not_good+=2


