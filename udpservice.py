#
# Copyright 2012-2013 eNovance <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import socket
import msgpack
from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
import six
import uuid
import datetime

from oslo_config import cfg
from ceilometer.openstack.common import log
from ceilometer.i18n import _, _LE
from ceilometer.openstack.common import service as os_service
from oslo_config import cfg
from oslo_utils import netutils
from oslo_utils import timeutils
from oslo_utils import units


OPTS = [
    cfg.StrOpt('udp_address',
               default='0.0.0.0',
               help='Address to which the UDP socket is bound. Set to '
               'an empty string to disable.'),
    cfg.IntOpt('udp_port',
               default=4952,
               help='Port to which the UDP socket is bound.'),
    cfg.StrOpt('acord_control_exchange',
               default='vcpeservice',
               help="Exchange name for VCPE notifications."),
    cfg.StrOpt('rabbit_userid',
               default='guest',
               help='rabbitmq server user id.'),
    cfg.StrOpt('rabbit_password',
               default='guest',
               help='rabbitmq server password'),
    cfg.StrOpt('rabbit_hosts',
               default='0.0.0.0',
               help='Address of rabbitmq server. '),
]

cfg.CONF.register_opts(OPTS, group="udpservice")

LOG = log.getLogger(__name__)


class UdpService(os_service.Service):
    """Listener for the udpservice service."""
    def start(self):
        """Bind the UDP socket and handle incoming data."""
        # ensure dispatcher is configured before starting other services
        super(UdpService, self).start()
         
        if cfg.CONF.udpservice.udp_address:
            self.tg.add_thread(self.start_udp)

    def convert_sample_to_event_data(self,msg):
        event_data = {'event_type': 'infra','message_id':six.text_type(uuid.uuid4()),'publisher_id': 'cpe_publisher_id','timestamp':datetime.datetime.now().isoformat(),'priority':'INFO','payload':msg}
        return event_data
    
    def setup_rabbit_mq_channel(self):
        service_exchange = Exchange(cfg.CONF.udpservice.acord_control_exchange, "topic", durable=False)
        rabbit_host = cfg.CONF.udpservice.rabbit_hosts
        rabbit_user = cfg.CONF.udpservice.rabbit_userid 
        rabbit_password = cfg.CONF.udpservice.rabbit_password
        # connections/channels
        connection = BrokerConnection(rabbit_host, rabbit_user, rabbit_password)
        print 'Connection to RabbitMQ server successful'
        channel = connection.channel()
        # produce
        self.producer = Producer(channel, exchange=service_exchange, routing_key='notifications.info')

    def start_udp(self):
        address_family = socket.AF_INET
        if netutils.is_valid_ipv6(cfg.CONF.udpservice.udp_address):
            address_family = socket.AF_INET6
        udp = socket.socket(address_family, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind((cfg.CONF.udpservice.udp_address,
                  cfg.CONF.udpservice.udp_port))

        self.setup_rabbit_mq_channel()
        self.udp_run = True
        while self.udp_run:
            # NOTE(jd) Arbitrary limit of 64K because that ought to be
            # enough for anybody.
            data, source = udp.recvfrom(64 * units.Ki)
            try:
                sample = msgpack.loads(data, encoding='utf-8')
            except Exception:
                LOG.warn(_("UDP: Cannot decode data sent by %s"), source)
            else:
                try:
                    if sample.has_key("event_type"):
                         LOG.debug(_("recevied event  :%s"),sample)
                         self.producer.publish(sample)
                    else:
                         LOG.debug(_("recevied Sample  :%s"),sample)
                         msg = self.convert_sample_to_event_data(sample)
                         self.producer.publish(msg)
                except Exception:
                    LOG.exception(_("UDP: Unable to store meter"))

    def stop(self):
        self.udp_run = False
        super(UdpService, self).stop()

