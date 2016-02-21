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

import abc

from oslo_config import cfg
import requests
from requests import auth
import six
import json

from ceilometer.i18n import _
from ceilometer.openstack.common import log


CONF = cfg.CONF
CONF.import_opt('http_timeout', 'ceilometer.service')


LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class _Base(object):
    """Base class of ONOS REST APIs Clients."""

    @abc.abstractproperty
    def base_url(self):
        """Returns base url for each REST API."""

    def __init__(self, client):
        self.client = client

    def request(self, path, container_name):
        return self.client.request(self.base_url + path, container_name)


class ONOSRESTAPIFailed(Exception):
    pass


class ONOSRESTAPIClient(_Base):
    """ONOS Statistics REST API Client

    Base URL:
      {endpoint}/onos/v1
    """

    base_url = '/onos/v1'

    def get_devices(self, container_name):
        """Get device informations

        URL:
            {Base URL}/devices
        """
        output = '{ "devices":[ \
                     { \
                        "id":"of:0000000000000001", \
                        "type":"SWITCH", \
                        "available":true, \
                        "role":"MASTER", \
                        "mfr":"Stanford University, Ericsson Research and CPqD Research", \
                        "hw":"OpenFlow 1.3 Reference Userspace Switch", \
                        "sw":"Apr  6 2015 16:10:53", \
                        "serial":"1", \
                        "chassisId":"1", \
                        "annotations":{"protocol":"OF_13","channelId":"192.168.10.50:39306"} \
                     }]}'

        return self.request('/devices', container_name)
        #LOG.info("SRIKANTH: Returning dummy ONOS devices output")
        #outputJson = json.loads(output)
        #return outputJson

    def get_flow_statistics(self, container_name):
        """Get flow statistics

        URL:
            {Base URL}/flows
        """
        output = '{"flows":[ \
                       { \
                          "deviceId":"of:0000000000000001", \
                          "id":"3377699721451393", \
                          "tableId":2, \
                          "appId":12, \
                          "groupId":0, \
                          "priority":100, \
                          "timeout":0, \
                          "isPermanent":true, \
                          "state":"PENDING_ADD", \
                          "life":0, \
                          "packets":0, \
                          "bytes":0, \
                          "lastSeen":1439355470576, \
                          "treatment":{"instructions":[],"deferred":[]}, \
                          "selector":{"criteria":[]} \
                      }]}'
        return self.request('/flows', container_name)
        #LOG.info("SRIKANTH: Returning dummy ONOS flow statistics output")
        #outputJson = json.loads(output)
        #return outputJson

    def get_port_statistics(self, container_name):
        """Get port statistics

        URL:
            {Base URL}/portstats
        """
        output = '{ "portstats": [ \
                      { \
                          "deviceId":"of:0000000000000001", \
                          "id":"3", \
                          "receivePackets": "182", \
                          "sentPackets": "173", \
                          "receiveBytes": "12740", \
                          "sentBytes": "12110", \
                          "receiveDrops": "740", \
                          "sentDrops": "110", \
                          "receiveErrors": "740", \
                          "sentErrors": "110", \
                          "receiveFrameError": "740", \
                          "receiveOverRunError": "740", \
                          "receiveCrcError": "740", \
                          "collisionCount": "110" \
                      }]}'
        #TODO Add Portstats REST API to ONOS
        return self.request('/statistics/ports', container_name)
        #LOG.info("SRIKANTH: Returning dummy ONOS port statistics output")
        #outputJson = json.loads(output)
        #return outputJson

    def get_table_statistics(self, container_name):
        """Get table statistics

        URL:
            {Base URL}/table
        """
        output = '{ \
                      "tableStatistics": [ \
                          { \
                              "deviceId":"of:0000000000000001", \
                              "id":"4", \
                              "activeCount": "11", \
                              "lookupCount": "816", \
                              "matchedCount": "220", \
                              "maximumEntries": "1000" \
                          } \
                       ] \
                    }'
        #TODO Add table statistics REST API to ONOS
        return self.request('/statistics/flows/tables', container_name)
        #LOG.info("SRIKANTH: Returning dummy ONOS table statistics output")
        #outputJson = json.loads(output)
        #return outputJson

class Client(object):

    def __init__(self, endpoint, params):
        self.rest_client = ONOSRESTAPIClient(self)

        self._endpoint = endpoint

        self._req_params = self._get_req_params(params)

    @staticmethod
    def _get_req_params(params):
        req_params = {
            'headers': {
                'Accept': 'application/json'
            },
            'timeout': CONF.http_timeout,
        }

        auth_way = params.get('auth')
        if auth_way in ['basic', 'digest']:
            user = params.get('user')
            password = params.get('password')

            if auth_way == 'basic':
                auth_class = auth.HTTPBasicAuth
            else:
                auth_class = auth.HTTPDigestAuth

            req_params['auth'] = auth_class(user, password)
        return req_params

    def _log_req(self, url):

        curl_command = ['REQ: curl -i -X GET ', '"%s" ' % (url)]

        if 'auth' in self._req_params:
            auth_class = self._req_params['auth']
            if isinstance(auth_class, auth.HTTPBasicAuth):
                curl_command.append('--basic ')
            else:
                curl_command.append('--digest ')

            curl_command.append('--user "%s":"%s" ' % (auth_class.username,
                                                       auth_class.password))

        for name, value in six.iteritems(self._req_params['headers']):
            curl_command.append('-H "%s: %s" ' % (name, value))

        LOG.debug(''.join(curl_command))

    @staticmethod
    def _log_res(resp):

        dump = ['RES: \n', 'HTTP %.1f %s %s\n' % (resp.raw.version,
                                                  resp.status_code,
                                                  resp.reason)]
        dump.extend('%s: %s\n' % (k, v)
                    for k, v in six.iteritems(resp.headers))
        dump.append('\n')
        if resp.content:
            dump.extend([resp.content, '\n'])

        LOG.debug(''.join(dump))

    def _http_request(self, url):
        if CONF.debug:
            self._log_req(url)
        resp = requests.get(url, **self._req_params)
        if CONF.debug:
            self._log_res(resp)
        if resp.status_code / 100 != 2:
            raise ONOSRESTAPIFailed(
                _('ONOS API returned %(status)s %(reason)s') %
                {'status': resp.status_code, 'reason': resp.reason})

        return resp.json()

    def request(self, path, container_name):

        url = self._endpoint + path % {'container_name': container_name}
        return self._http_request(url)
