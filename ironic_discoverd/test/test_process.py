# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import time

import eventlet
from ironicclient import exceptions
import mock

from ironic_discoverd import conf
from ironic_discoverd import firewall
from ironic_discoverd import node_cache
from ironic_discoverd.plugins import example as example_plugin
from ironic_discoverd import process
from ironic_discoverd.test import base as test_base
from ironic_discoverd import utils


class BaseTest(test_base.NodeTest):
    def setUp(self):
        super(BaseTest, self).setUp()
        conf.CONF.set('discoverd', 'processing_hooks',
                      'ramdisk_error,scheduler,validate_interfaces')
        self.started_at = time.time()
        self.all_macs = self.macs + ['DE:AD:BE:EF:DE:AD']
        self.data = {
            'ipmi_address': self.bmc_address,
            'cpus': 2,
            'cpu_arch': 'x86_64',
            'memory_mb': 1024,
            'local_gb': 20,
            'interfaces': {
                'em1': {'mac': self.macs[0], 'ip': '1.2.0.1'},
                'em2': {'mac': self.macs[1], 'ip': '1.2.0.2'},
                'em3': {'mac': self.all_macs[2]},
            }
        }
        self.ports = [
            mock.Mock(uuid='port_uuid%d' % i, address=mac)
            for i, mac in enumerate(self.macs)
        ]


@mock.patch.object(process, '_process_node', autospec=True)
@mock.patch.object(node_cache, 'pop_node', autospec=True)
@mock.patch.object(utils, 'get_client', autospec=True)
class TestProcess(BaseTest):
    def setUp(self):
        super(TestProcess, self).setUp()
        self.fake_node_json = 'node json'

    def prepate_mocks(func):
        @functools.wraps(func)
        def wrapper(self, client_mock, pop_mock, process_mock):
            cli = client_mock.return_value
            pop_mock.return_value = node_cache.NodeInfo(
                uuid=self.node.uuid,
                started_at=self.started_at)
            cli.port.create.side_effect = self.ports
            cli.node.get.return_value = self.node
            process_mock.return_value.to_dict.return_value = (
                self.fake_node_json)

            return func(self, cli, pop_mock, process_mock)

        return wrapper

    @prepate_mocks
    def test_ok(self, cli, pop_mock, process_mock):
        res = process.process(self.data)

        self.assertEqual({'node': self.fake_node_json}, res)

        # By default interfaces w/o IP are dropped
        self.assertEqual(['em1', 'em2'], sorted(self.data['interfaces']))
        self.assertEqual(self.macs, sorted(self.data['macs']))

        pop_mock.assert_called_once_with(bmc_address=self.bmc_address,
                                         mac=self.data['macs'])
        cli.node.get.assert_called_once_with(self.uuid)
        process_mock.assert_called_once_with(cli, cli.node.get.return_value,
                                             self.data, pop_mock.return_value)

    @prepate_mocks
    def test_no_ipmi(self, cli, pop_mock, process_mock):
        del self.data['ipmi_address']
        res = process.process(self.data)

        self.assertEqual({'node': self.fake_node_json}, res)

        pop_mock.assert_called_once_with(bmc_address=None,
                                         mac=self.data['macs'])
        cli.node.get.assert_called_once_with(self.uuid)
        process_mock.assert_called_once_with(cli, cli.node.get.return_value,
                                             self.data, pop_mock.return_value)

    @prepate_mocks
    def test_deprecated_macs(self, cli, pop_mock, process_mock):
        del self.data['interfaces']
        self.data['macs'] = self.macs
        res = process.process(self.data)

        self.assertEqual({'node': self.fake_node_json}, res)

        self.assertEqual(self.macs, sorted(i['mac'] for i in
                                           self.data['interfaces'].values()))
        self.assertEqual(self.macs, sorted(self.data['macs']))

        pop_mock.assert_called_once_with(bmc_address=self.bmc_address,
                                         mac=self.data['macs'])
        cli.node.get.assert_called_once_with(self.uuid)
        process_mock.assert_called_once_with(cli, cli.node.get.return_value,
                                             self.data, pop_mock.return_value)

    @prepate_mocks
    def test_ports_for_inactive(self, cli, pop_mock, process_mock):
        conf.CONF.set('discoverd', 'ports_for_inactive_interfaces', 'true')
        res = process.process(self.data)

        self.assertEqual({'node': self.fake_node_json}, res)

        self.assertEqual(['em1', 'em2', 'em3'],
                         sorted(self.data['interfaces']))
        self.assertEqual(self.all_macs, sorted(self.data['macs']))

        pop_mock.assert_called_once_with(bmc_address=self.bmc_address,
                                         mac=self.data['macs'])
        cli.node.get.assert_called_once_with(self.uuid)
        process_mock.assert_called_once_with(cli, cli.node.get.return_value,
                                             self.data, pop_mock.return_value)

    @prepate_mocks
    def test_invalid_interfaces(self, cli, pop_mock, process_mock):
        self.data['interfaces'] = {
            'br1': {'mac': 'broken', 'ip': '1.2.0.1'},
            'br2': {'mac': '', 'ip': '1.2.0.2'},
            'br3': {},
        }

        process.process(self.data)

        self.assertEqual({}, self.data['interfaces'])
        self.assertEqual([], self.data['macs'])

        pop_mock.assert_called_once_with(bmc_address=self.bmc_address,
                                         mac=[])
        cli.node.get.assert_called_once_with(self.uuid)
        process_mock.assert_called_once_with(cli, cli.node.get.return_value,
                                             self.data, pop_mock.return_value)

    @prepate_mocks
    def test_error(self, cli, pop_mock, process_mock):
        self.data['error'] = 'BOOM'

        self.assertRaisesRegexp(utils.DiscoveryFailed,
                                'BOOM',
                                process.process, self.data)
        self.assertFalse(process_mock.called)

    @prepate_mocks
    def test_missing_required(self, cli, pop_mock, process_mock):
        del self.data['cpus']

        self.assertRaisesRegexp(utils.DiscoveryFailed,
                                'missing',
                                process.process, self.data)
        self.assertFalse(process_mock.called)

    @prepate_mocks
    def test_not_found_in_cache(self, cli, pop_mock, process_mock):
        pop_mock.side_effect = utils.DiscoveryFailed('not found')

        self.assertRaisesRegexp(utils.DiscoveryFailed,
                                'not found',
                                process.process, self.data)
        self.assertFalse(cli.node.get.called)
        self.assertFalse(process_mock.called)

    @prepate_mocks
    def test_not_found_in_ironic(self, cli, pop_mock, process_mock):
        cli.node.get.side_effect = exceptions.NotFound()

        self.assertRaisesRegexp(utils.DiscoveryFailed,
                                'not found',
                                process.process, self.data)
        cli.node.get.assert_called_once_with(self.uuid)
        self.assertFalse(process_mock.called)


@mock.patch.object(eventlet.greenthread, 'spawn_n',
                   lambda f, *a: f(*a) and None)
@mock.patch.object(eventlet.greenthread, 'sleep', lambda _: None)
@mock.patch.object(example_plugin.ExampleProcessingHook, 'post_discover')
@mock.patch.object(firewall, 'update_filters', autospec=True)
class TestProcessNode(BaseTest):
    def setUp(self):
        super(TestProcessNode, self).setUp()
        conf.CONF.set('discoverd', 'processing_hooks',
                      'ramdisk_error,scheduler,validate_interfaces,example')
        self.data['macs'] = self.macs  # validate_interfaces hook
        self.cached_node = node_cache.NodeInfo(uuid=self.uuid,
                                               started_at=self.started_at)
        self.power_off_repeats = 5
        self.patch_before = [
            {'op': 'add', 'path': '/properties/cpus', 'value': '2'},
            {'op': 'add', 'path': '/properties/memory_mb', 'value': '1024'},
        ]  # scheduler hook
        self.patch_after = [
            {'op': 'add', 'path': '/extra/newly_discovered', 'value': 'true'},
            {'op': 'remove', 'path': '/extra/on_discovery'},
        ]

        self.cli = mock.Mock()
        self.cli.node.get.side_effect = self.fake_get()
        self.cli.port.create.side_effect = self.ports
        self.cli.node.update.return_value = self.node

    def fake_get(self):
        # Simulate long power off
        for _ in range(self.power_off_repeats):
            yield self.node
        self.node.power_state = 'power off'
        yield self.node

    def call(self):
        return process._process_node(self.cli, self.node, self.data,
                                     self.cached_node)

    def test_ok(self, filters_mock, post_hook_mock):
        self.call()

        self.cli.node.get.assert_called_with(self.uuid)
        self.assertEqual(self.power_off_repeats + 1,
                         self.cli.node.get.call_count)
        self.cli.port.create.assert_any_call(node_uuid=self.uuid,
                                             address=self.macs[0])
        self.cli.port.create.assert_any_call(node_uuid=self.uuid,
                                             address=self.macs[1])
        self.cli.node.update.assert_any_call(self.uuid, self.patch_before)
        self.cli.node.update.assert_any_call(self.uuid, self.patch_after)
        self.assertFalse(self.cli.node.set_power_state.called)

        post_hook_mock.assert_called_once_with(self.node, mock.ANY,
                                               self.data)
        # List is built from a dict - order is undefined
        self.assertEqual(self.ports, sorted(post_hook_mock.call_args[0][1],
                                            key=lambda p: p.address))

    def test_port_failed(self, filters_mock, post_hook_mock):
        self.ports[0] = exceptions.Conflict()

        self.call()

        self.cli.port.create.assert_any_call(node_uuid=self.uuid,
                                             address=self.macs[0])
        self.cli.port.create.assert_any_call(node_uuid=self.uuid,
                                             address=self.macs[1])
        self.cli.node.update.assert_any_call(self.uuid, self.patch_before)
        self.cli.node.update.assert_any_call(self.uuid, self.patch_after)

        post_hook_mock.assert_called_once_with(self.node, self.ports[1:],
                                               self.data)

    def test_hook_patches(self, filters_mock, post_hook_mock):
        node_patches = ['node patch1', 'node patch2']
        port_patch = ['port patch']
        post_hook_mock.return_value = (node_patches,
                                       {self.macs[1]: port_patch})

        self.call()

        self.cli.node.update.assert_any_call(self.uuid,
                                             self.patch_before + node_patches)
        self.cli.node.update.assert_any_call(self.uuid, self.patch_after)
        self.cli.port.update.assert_called_once_with(self.ports[1].uuid,
                                                     port_patch)

    @mock.patch.object(time, 'time')
    def test_power_timeout(self, time_mock, filters_mock, post_hook_mock):
        conf.CONF.set('discoverd', 'timeout', '100')
        time_mock.return_value = self.started_at + 1000

        self.call()

        self.cli.node.update.assert_called_once_with(self.uuid,
                                                     self.patch_before)

    def test_force_power_off(self, filters_mock, post_hook_mock):
        conf.CONF.set('discoverd', 'power_off_after_discovery', 'true')

        self.call()

        self.cli.node.set_power_state.assert_called_once_with(self.uuid, 'off')

    def test_force_power_off_failed(self, filters_mock, post_hook_mock):
        conf.CONF.set('discoverd', 'power_off_after_discovery', 'true')
        self.cli.node.set_power_state.side_effect = exceptions.Conflict()

        self.assertRaisesRegexp(utils.DiscoveryFailed, 'Failed to power off',
                                self.call)

        self.cli.node.set_power_state.assert_called_once_with(self.uuid, 'off')
        self.cli.node.update.assert_called_once_with(self.uuid,
                                                     self.patch_before)