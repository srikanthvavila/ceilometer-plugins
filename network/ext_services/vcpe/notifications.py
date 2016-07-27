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
    cfg.StrOpt('vsgservice_control_exchange',
               default='vcpeservice',
               help="Exchange name for VCPE notifications."),
]

cfg.CONF.register_opts(OPTS)

LOG = log.getLogger(__name__)


class VCPENotificationBase(plugin_base.NotificationBase):

    resource_name = None

    def get_targets(self,conf):
        """Return a sequence of oslo.messaging.Target

        This sequence is defining the exchange and topics to be connected for
        this plugin.
        """
        LOG.info("SRIKANTH: get_targets for VCPE Notification Listener")
        return [oslo_messaging.Target(topic=topic,
                                      exchange=conf.vsgservice_control_exchange)
                for topic in self.get_notification_topics(conf)]

class VCPENotification(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe$']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE notification: vcpe_id=%(vcpe_id)s' % {'vcpe_id': message['payload']['vcpe_id']})
        yield sample.Sample.from_notification(
            name='vsg',
            type=sample.TYPE_GAUGE,
            unit='vsg',
            volume=1,
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=message['payload']['vcpe_id'],
            message=message)

class VCPEComputeStatistics(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.compute.stats']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE event vcpe.compute.stats')
        if message['payload']:
            if 'cpu_util' in message['payload']:
                yield sample.Sample.from_notification(
                    name='cpu_util',
                    type=sample.TYPE_GAUGE,
                    unit='%',
                    volume=float(message['payload']['cpu_util']),
                    user_id=message['payload']['user_id'],
                    project_id=message['payload']['tenant_id'],
                    resource_id=message['payload']['vcpe_id'],
                    message=message)
            if 'memory' in message['payload']:
                yield sample.Sample.from_notification(
                    name='memory',
                    type=sample.TYPE_GAUGE,
                    unit='MB',
                    volume=float(message['payload']['memory']),
                    user_id=message['payload']['user_id'],
                    project_id=message['payload']['tenant_id'],
                    resource_id=message['payload']['vcpe_id'],
                    message=message)
            if 'memory_usage' in message['payload']:
                yield sample.Sample.from_notification(
                    name='memory.usage',
                    type=sample.TYPE_GAUGE,
                    unit='MB',
                    volume=float(message['payload']['memory_usage']),
                    user_id=message['payload']['user_id'],
                    project_id=message['payload']['tenant_id'],
                    resource_id=message['payload']['vcpe_id'],
                    message=message)
            if 'network_stats' in message['payload']:
                for intf in message['payload']['network_stats']:
                    resource_id = message['payload']['vcpe_id'] + '-' + intf['intf']
                    if 'rx_bytes' in intf:
                        yield sample.Sample.from_notification(
                            name='network.incoming.bytes',
                            type=sample.TYPE_CUMULATIVE,
                            unit='B',
                            volume=float(intf['rx_bytes']),
                            user_id=message['payload']['user_id'],
                            project_id=message['payload']['tenant_id'],
                            resource_id=resource_id,
                            message=message)
                    if 'tx_bytes' in intf:
                        yield sample.Sample.from_notification(
                            name='network.outgoing.bytes',
                            type=sample.TYPE_CUMULATIVE,
                            unit='B',
                            volume=float(intf['tx_bytes']),
                            user_id=message['payload']['user_id'],
                            project_id=message['payload']['tenant_id'],
                            resource_id=resource_id,
                            message=message)
                    if 'rx_packets' in intf:
                        yield sample.Sample.from_notification(
                            name='network.incoming.packets',
                            type=sample.TYPE_CUMULATIVE,
                            unit='packet',
                            volume=float(intf['rx_packets']),
                            user_id=message['payload']['user_id'],
                            project_id=message['payload']['tenant_id'],
                            resource_id=resource_id,
                            message=message)
                    if 'tx_packets' in intf:
                        yield sample.Sample.from_notification(
                            name='network.outgoing.packets',
                            type=sample.TYPE_CUMULATIVE,
                            unit='packet',
                            volume=float(intf['tx_packets']),
                            user_id=message['payload']['user_id'],
                            project_id=message['payload']['tenant_id'],
                            resource_id=resource_id,
                            message=message)

class VCPEDNSCacheSize(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.cache.size']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE cache.size notification')
        yield sample.Sample.from_notification(
            name='vsg.dns.cache.size',
            type=sample.TYPE_GAUGE,
            unit='entries',
            volume=float(message['payload']['cache_size']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=message['payload']['vcpe_id'],
            message=message)

class VCPEDNSTotalInsertedEntries(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.total_instered_entries']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE total_instered_entries notification')
        yield sample.Sample.from_notification(
            name='vsg.dns.total_instered_entries',
            type=sample.TYPE_CUMULATIVE,
            unit='entries',
            volume=float(message['payload']['total_instered_entries']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=message['payload']['vcpe_id'],
            message=message)

class VCPEDNSReplacedUnexpiredEntries(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.replaced_unexpired_entries']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE replaced_unexpired_entries notification')
        yield sample.Sample.from_notification(
            name='vsg.dns.replaced_unexpired_entries',
            type=sample.TYPE_CUMULATIVE,
            unit='entries',
            volume=float(message['payload']['replaced_unexpired_entries']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=message['payload']['vcpe_id'],
            message=message)

class VCPEDNSQueriesForwarded(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.queries_forwarded']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE queries_forwarded notification')
        yield sample.Sample.from_notification(
            name='vsg.dns.queries_forwarded',
            type=sample.TYPE_CUMULATIVE,
            unit='queries',
            volume=float(message['payload']['queries_forwarded']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=message['payload']['vcpe_id'],
            message=message)

class VCPEDNSQueriesAnsweredLocally(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.queries_answered_locally']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE queries_answered_locally notification')
        yield sample.Sample.from_notification(
            name='vsg.dns.queries_answered_locally',
            type=sample.TYPE_CUMULATIVE,
            unit='queries',
            volume=float(message['payload']['queries_answered_locally']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=message['payload']['vcpe_id'],
            message=message)

class VCPEDNSServerQueriesSent(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.server.queries_sent']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE server.queries_sent notification')
        resource_id = message['payload']['vcpe_id'] + '-' + message['payload']['upstream_server']
        yield sample.Sample.from_notification(
            name='vsg.dns.server.queries_sent',
            type=sample.TYPE_CUMULATIVE,
            unit='queries',
            volume=float(message['payload']['queries_sent']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=resource_id,
            message=message)

class VCPEDNSServerQueriesFailed(VCPENotificationBase):

    resource_name = None
    event_types = ['vcpe.dns.server.queries_failed']

    def process_notification(self, message):
        LOG.info('SRIKANTH: Received VCPE server.queries_failed notification')
        resource_id = message['payload']['vcpe_id'] + '-' + message['payload']['upstream_server']
        yield sample.Sample.from_notification(
            name='vsg.dns.server.queries_failed',
            type=sample.TYPE_CUMULATIVE,
            unit='queries',
            volume=float(message['payload']['queries_failed']),
            user_id=message['payload']['user_id'],
            project_id=message['payload']['tenant_id'],
            resource_id=resource_id,
            message=message)

