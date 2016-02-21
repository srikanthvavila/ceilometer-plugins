#
# Copyright 2013 NEC Corporation.  All rights reserved.
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
from oslo_utils import timeutils
import six
from six import moves
from six.moves.urllib import parse as urlparse

from ceilometer.i18n import _
from ceilometer.network.statistics import driver
from ceilometer.network.statistics.onos import client
from ceilometer.openstack.common import log
from ceilometer import utils


LOG = log.getLogger(__name__)


def _get_properties(properties, prefix='properties'):
    resource_meta = {}
    if properties is not None:
        for k, v in six.iteritems(properties):
            value = v['value']
            key = prefix + '_' + k
            if 'name' in v:
                key += '_' + v['name']
            resource_meta[key] = value
    return resource_meta


def _get_int_sample(key, statistic, resource_id, resource_meta):
    if key not in statistic:
        return None
    return int(statistic[key]), resource_id, resource_meta


class ONOSDriver(driver.Driver):
    """Driver of network info collector from ONOS.

    This driver uses resources in "pipeline.yaml".
    Resource requires below conditions:

    * resource is url
    * scheme is "onos"

    This driver can be configured via query parameters.
    Supported parameters:

    * scheme:
      The scheme of request url to ONOS REST API endpoint.
      (default http)
    * auth:
      Auth strategy of http.
      This parameter can be set basic and digest.(default None)
    * user:
      This is username that is used by auth.(default None)
    * password:
      This is password that is used by auth.(default None)
    * container_name:
      Name of container of ONOS.(default "default")
      This parameter allows multi vaues.

    e.g.::

      onos://127.0.0.1:8181/onos/v1?auth=basic&user=admin&password=admin&scheme=http

    In this case, the driver send request to below URLs:

      http://127.0.0.1:8181/onos/v1/flows
    """
    @staticmethod
    def _prepare_cache(endpoint, params, cache):

        if 'network.statistics.onos' in cache:
            return cache['network.statistics.onos']

        data = {}

        container_names = params.get('container_name', ['default'])

        onos_params = {}
        if 'auth' in params:
            onos_params['auth'] = params['auth'][0]
        if 'user' in params:
            onos_params['user'] = params['user'][0]
        if 'password' in params:
            onos_params['password'] = params['password'][0]
        cs = client.Client(endpoint, onos_params)

        for container_name in container_names:
            try:
                container_data = {}

                # get flow statistics
                container_data['flow'] = cs.rest_client.get_flow_statistics(
                    container_name)

                # get port statistics
                container_data['port'] = cs.rest_client.get_port_statistics(
                    container_name)

                # get table statistics
                container_data['table'] = cs.rest_client.get_table_statistics(
                    container_name)

                # get topology
                #container_data['topology'] = cs.topology.get_topology(
                #    container_name)

                # get switch informations
                container_data['switch'] = cs.rest_client.get_devices(
                    container_name)

                container_data['timestamp'] = timeutils.isotime()

                data[container_name] = container_data
            except Exception:
                LOG.exception(_('Request failed to connect to ONOS'
                                ' with NorthBound REST API'))

        cache['network.statistics.onos'] = data

        return data

    def get_sample_data(self, meter_name, parse_url, params, cache):

        extractor = self._get_extractor(meter_name)
        if extractor is None:
            # The way to getting meter is not implemented in this driver or
            # ONOS REST API has not api to getting meter.
            return None

        iter = self._get_iter(meter_name)
        if iter is None:
            # The way to getting meter is not implemented in this driver or
            # ONOS REST API has not api to getting meter.
            return None

        parts = urlparse.ParseResult(params.get('scheme', ['http'])[0],
                                     parse_url.netloc,
                                     parse_url.path,
                                     None,
                                     None,
                                     None)
        endpoint = urlparse.urlunparse(parts)

        data = self._prepare_cache(endpoint, params, cache)

        samples = []
        for name, value in six.iteritems(data):
            timestamp = value['timestamp']
            for sample in iter(extractor, value):
                if sample is not None:
                    # set controller name and container name
                    # to resource_metadata
                    sample[2]['controller'] = 'ONOS'
                    sample[2]['container'] = name

                    samples.append(sample + (timestamp, ))

        return samples

    def _get_iter(self, meter_name):
        if meter_name == 'switch':
            return self._iter_switch
        elif meter_name.startswith('switch.flow'):
            return self._iter_flow
        elif meter_name.startswith('switch.table'):
            return self._iter_table
        elif meter_name.startswith('switch.port'):
            return self._iter_port

    def _get_extractor(self, meter_name):
        method_name = '_' + meter_name.replace('.', '_')
        return getattr(self, method_name, None)

    @staticmethod
    def _iter_switch(extractor, data):
        for switch in data['switch']['devices']:
            yield extractor(switch, switch['id'], {})

    @staticmethod
    def _switch(statistic, resource_id, resource_meta):

        for key in ['mfr','hw','sw','available']:
            resource_meta[key] = statistic[key]
        for key in ['protocol','channelId']:
            resource_meta[key] = statistic['annotations'][key]

        return 1, resource_id, resource_meta

    @staticmethod
    def _iter_port(extractor, data):
        for statistic in data['port']['statistics']:
            for port_statistic in statistic['ports']:
                 resource_meta = {'port': port_statistic['port']}
                 yield extractor(port_statistic, statistic['device'],
                                resource_meta, data)

    @staticmethod
    def _switch_port(statistic, resource_id, resource_meta, data):
        return 1, resource_id, resource_meta

    @staticmethod
    def _switch_port_receive_packets(statistic, resource_id,
                                     resource_meta, data):
        return _get_int_sample('packetsReceived', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_transmit_packets(statistic, resource_id,
                                      resource_meta, data):
        return _get_int_sample('packetsSent', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_receive_bytes(statistic, resource_id,
                                   resource_meta, data):
        return _get_int_sample('bytesReceived', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_transmit_bytes(statistic, resource_id,
                                    resource_meta, data):
        return _get_int_sample('bytesSent', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_receive_drops(statistic, resource_id,
                                   resource_meta, data):
        return _get_int_sample('packetsRxDropped', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_transmit_drops(statistic, resource_id,
                                    resource_meta, data):
        return _get_int_sample('packetsTxDropped', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_receive_errors(statistic, resource_id,
                                    resource_meta, data):
        return _get_int_sample('packetsRxErrors', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_transmit_errors(statistic, resource_id,
                                     resource_meta, data):
        return _get_int_sample('packetsTxErrors', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_port_receive_frame_error(statistic, resource_id,
                                         resource_meta, data):
        #return _get_int_sample('receiveFrameError', statistic, resource_id,
        #                       resource_meta)
        return 0, resource_id, resource_meta

    @staticmethod
    def _switch_port_receive_overrun_error(statistic, resource_id,
                                           resource_meta, data):
        #return _get_int_sample('receiveOverRunError', statistic, resource_id,
        #                       resource_meta)
        return 0, resource_id, resource_meta

    @staticmethod
    def _switch_port_receive_crc_error(statistic, resource_id,
                                       resource_meta, data):
        #return _get_int_sample('receiveCrcError', statistic, resource_id,
        #                       resource_meta)
        return 0, resource_id, resource_meta

    @staticmethod
    def _switch_port_collision_count(statistic, resource_id,
                                     resource_meta, data):
        #return _get_int_sample('collisionCount', statistic, resource_id,
        #                       resource_meta)
        return 0, resource_id, resource_meta

    @staticmethod
    def _iter_table(extractor, data):
        for statistic in data['table']['statistics']:
            for table_statistic in statistic['table']:
                 resource_meta = {'table_id': table_statistic['tableId']}
                 yield extractor(table_statistic,
                            statistic['device'],
                            resource_meta)

    @staticmethod
    def _switch_table(statistic, resource_id, resource_meta):
        return 1, resource_id, resource_meta

    @staticmethod
    def _switch_table_active_entries(statistic, resource_id,
                                     resource_meta):
        return _get_int_sample('activeEntries', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_table_lookup_packets(statistic, resource_id,
                                     resource_meta):
        return _get_int_sample('packetsLookedUp', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_table_matched_packets(statistic, resource_id,
                                      resource_meta):
        return _get_int_sample('packetsMathced', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _iter_flow(extractor, data):
        for flow_statistic in data['flow']['flows']:
            resource_meta = {'flow_id': flow_statistic['id'],
                             'table_id': flow_statistic['tableId'],
                             'priority': flow_statistic['priority'],
                             'state': flow_statistic['state']}
            yield extractor(flow_statistic,
                            flow_statistic['deviceId'],
                            resource_meta)

    @staticmethod
    def _switch_flow(statistic, resource_id, resource_meta):
        return 1, resource_id, resource_meta

    @staticmethod
    def _switch_flow_duration_seconds(statistic, resource_id,
                                      resource_meta):
        if 'life' not in statistic:
            return None
        return int(statistic['life']/1000), resource_id, resource_meta

    @staticmethod
    def _switch_flow_duration_nanoseconds(statistic, resource_id,
                                          resource_meta):
        if 'life' not in statistic:
            return None
        return int(statistic['life']*1000), resource_id, resource_meta

    @staticmethod
    def _switch_flow_packets(statistic, resource_id, resource_meta):
        return _get_int_sample('packets', statistic, resource_id,
                               resource_meta)

    @staticmethod
    def _switch_flow_bytes(statistic, resource_id, resource_meta):
        return _get_int_sample('bytes', statistic, resource_id,
                               resource_meta)
