from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
import six
import uuid
import datetime

keystone_tenant_id='3a397e70f64e4e40b69b6266c634d9d0'
keystone_user_id='1e3ce043029547f1a61c1996d1a531a2'
rabbit_user='stackrabbit'
rabbit_password='xxxx'
rabbit_host='10.45.16.205'
vcpeservice_rabbit_exchange='vcpeservice'
cpe_publisher_id='vcpe_publisher'

producer = None

def setup_rabbit_mq_channel():
     global producer
     global rabbit_user, rabbit_password, rabbit_host, vcpeservice_rabbit_exchange,cpe_publisher_id
     vcpeservice_exchange = Exchange(vcpeservice_rabbit_exchange, "topic", durable=False)
     # connections/channels
     connection = BrokerConnection(rabbit_host, rabbit_user, rabbit_password)
     print 'Connection to RabbitMQ server successful'
     channel = connection.channel()
     # produce
     producer = Producer(channel, exchange=vcpeservice_exchange, routing_key='notifications.info')

def publish_cpe_stats():
     global producer
     global keystone_tenant_id, keystone_user_id, cpe_publisher_id

     msg = {'event_type': 'vcpe',
            'message_id':six.text_type(uuid.uuid4()),
            'publisher_id': cpe_publisher_id,
            'timestamp':datetime.datetime.now().isoformat(),
            'priority':'INFO',
            'payload': {'vcpe_id':'vcpe-222-432',
                        'user_id': keystone_user_id,
                        'tenant_id': keystone_tenant_id
                       }
           }
     producer.publish(msg)
     msg = {'event_type': 'vcpe.dns.cache.size',
            'message_id':six.text_type(uuid.uuid4()),
            'publisher_id': cpe_publisher_id,
            'timestamp':datetime.datetime.now().isoformat(),
            'priority':'INFO',
            'payload': {'vcpe_id':'vcpe-222-432',
                        'user_id': keystone_user_id,
                        'tenant_id': keystone_tenant_id,
                        'cache_size':150
                       }
            }           
     producer.publish(msg)

if __name__ == "__main__":
   setup_rabbit_mq_channel()
   publish_cpe_stats()
