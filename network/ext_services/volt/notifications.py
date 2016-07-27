#
# Copyright 2012 New Dream Network, LLC (DreamHost)
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
"""Handler for producing network counter messages from Neutron notification
   events.

"""

import oslo_messaging
from oslo_config import cfg

from ceilometer.agent import plugin_base
from oslo_log import log
from ceilometer import sample

OPTS = [
    cfg.StrOpt('voltservice_control_exchange',
               default='voltlistener',
               help="Exchange name for VOLT notifications."),
]

cfg.CONF.register_opts(OPTS)

LOG = log.getLogger(__name__)


class VOLTNotificationBase(plugin_base.NotificationBase):

    resource_name = None

    def get_targets(self,conf):
        """Return a sequence of oslo.messaging.Target

        This sequence is defining the exchange and topics to be connected for
        this plugin.
        """
        LOG.info("SRIKANTH: get_targets for VOLT Notification Listener")
        return [oslo_messaging.Target(topic=topic,
                                      exchange=conf.voltservice_control_exchange)
                for topic in self.get_notification_topics(conf)]

class VOLTDeviceNotification(VOLTNotificationBase):
    resource_name = 'volt.device'
    event_types = ['volt.device','volt.device.disconnect']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VOLT notification')
        yield sample.Sample.from_notification(
            name=message['event_type'],
            type=sample.TYPE_GAUGE,
            unit='olt',
            volume=1,
            user_id=message['payload']['user_id'],
            project_id=message['payload']['project_id'],
            resource_id=message['payload']['id'],
            message=message)

class VOLTDeviceSubscriberNotification(VOLTNotificationBase):
    resource_name = 'volt.device.subscriber'
    event_types = ['volt.device.subscriber','volt.device.subscriber.unregister']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VOLT notification')
        resource_id = message['payload']['id'] + '-' + message['payload']['subscriber_id']
        yield sample.Sample.from_notification(
            name=message['event_type'],
            type=sample.TYPE_GAUGE,
            unit='subscriber',
            volume=1,
            user_id=message['payload']['user_id'],
            project_id=message['payload']['project_id'],
            resource_id=resource_id,
            message=message)


