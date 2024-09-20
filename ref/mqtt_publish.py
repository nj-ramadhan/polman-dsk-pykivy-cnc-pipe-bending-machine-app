# python 3.6

import random
import time

from paho.mqtt import client as mqtt_client


broker = 'broker.hivemq.com'
# broker = 'demo.thingsboard.io/dashboard/'
port = 1883
topic = "v1/devices"
# Generate a Client ID with the publish prefix.
client_id = f'publish-{random.randint(0, 1000)}'
# username = 'emqx'
# password = 'public'

mqtt_broker = 'broker.hivemq.com'
# mqtt_broker = 'demo.thingsboard.io/dashboard/'
mqtt_port = 1883
mqtt_topic_machine_status = "machine-status/"
mqtt_topic_product_name = "product-name/"
mqtt_topic_production_target = "production-target/"
mqtt_topic_production_result = "production-result/"
# Generate a Client ID with the publish prefix.
mqtt_client_id = f'publish-rafindo-cnc-pipe-001'
# username = 'emqx'
# password = 'public'
flag_run = True
str_product_name = "bracket 870"
val_advanced_prod_qty = 100
val_prod_qty_result = 0

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def publish(client):
    global val_prod_qty_result
    msg_count = 1
    while True:
        time.sleep(1)
        msg = f"{msg_count * 20}"
        result = client.publish(topic, val_prod_qty_result)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Send `{val_prod_qty_result}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic {topic}")

        val_prod_qty_result += 1
        msg_count += 1
        if msg_count > 5:
            break

def mqtt_connect():
    global mqtt_broker, mqtt_port, mqtt_client_id
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(mqtt_client_id)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(mqtt_broker, mqtt_port)
    return client

def mqtt_publish(client, machine_status, str_product_name, production_target, production_result):
    global mqtt_topic_machine_status, mqtt_topic_product_name, mqtt_topic_production_target, mqtt_topic_production_result

    result = client.publish(mqtt_topic_machine_status, machine_status)
    status = result[0]
    if status == 0:
        print(f"Send `{machine_status}` to topic `{mqtt_topic_machine_status}`")
    else:
        print(f"Failed to send message to topic {mqtt_topic_machine_status}")

    result = client.publish(mqtt_topic_product_name, str_product_name)
    status = result[0]
    if status == 0:
        print(f"Send `{str_product_name}` to topic `{mqtt_topic_product_name}`")
    else:
        print(f"Failed to send message to topic {mqtt_topic_production_target}")

    result = client.publish(mqtt_topic_production_target, production_target)
    status = result[0]
    if status == 0:
        print(f"Send `{production_target}` to topic `{mqtt_topic_production_target}`")
    else:
        print(f"Failed to send message to topic {mqtt_topic_production_target}")

    result = client.publish(mqtt_topic_production_result, production_result)
    status = result[0]
    if status == 0:
        print(f"Send `{production_result}` to topic `{mqtt_topic_production_result}`")
    else:
        print(f"Failed to send message to topic {mqtt_topic_production_result}")

def run():
    global val_prod_qty_result
    mqtt_client = mqtt_connect()
    mqtt_client.loop_start()
    for i in range(10):
        mqtt_publish(mqtt_client, flag_run, str_product_name, val_advanced_prod_qty, val_prod_qty_result)
        val_prod_qty_result += 1
    mqtt_client.loop_stop()    
    # client = connect_mqtt()
    # client.loop_start()
    # publish(client)
    # client.loop_stop()


if __name__ == '__main__':
    run()
