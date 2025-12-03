import 'package:flutter/material.dart';
import '../models/scan.dart';
import '../services/api_service.dart';
import 'package:universal_html/html.dart' as html;

class HostsListScreen extends StatefulWidget {
  final bool vmsOnly;
  
  const HostsListScreen({Key? key, this.vmsOnly = false}) : super(key: key);

  @override
  _HostsListScreenState createState() => _HostsListScreenState();
}

class _HostsListScreenState extends State<HostsListScreen> {
  final ApiService _apiService = ApiService();
  List<Host> _hosts = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHosts();
  }

  Future<void> _loadHosts() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final hosts = widget.vmsOnly
          ? await _apiService.getUniqueVMs()
          : await _apiService.getUniqueHosts();
      setState(() {
        _hosts = hosts;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.vmsOnly ? 'Virtual Machines' : 'All Hosts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadHosts,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadHosts,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_hosts.isEmpty) {
      return Center(
        child: Text(
          widget.vmsOnly ? 'No VMs found' : 'No hosts found',
          style: const TextStyle(fontSize: 18, color: Colors.grey),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadHosts,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _hosts.length,
        itemBuilder: (context, index) {
          final host = _hosts[index];
          return _buildHostCard(host);
        },
      ),
    );
  }

  Widget _buildHostCard(Host host) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ExpansionTile(
        leading: Icon(
          host.isVm == true ? Icons.cloud_circle : Icons.computer,
          color: host.status == 'up' ? Colors.green : Colors.grey,
        ),
        title: Text(
          host.hostname ?? host.ipAddress,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (host.hostname != null) Text(host.ipAddress),
            if (host.osType != null)
              Text('OS: ${host.osType}', style: TextStyle(fontSize: 12, color: Colors.grey[600])),
            if (host.isVm == true && host.vmType != null)
              Text('VM: ${host.vmType}', style: TextStyle(fontSize: 12, color: Colors.blue[600])),
          ],
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (host.mac != null)
                  _buildInfoRow('MAC', host.mac!),
                if (host.vendor != null)
                  _buildInfoRow('Vendor', host.vendor!),
                if (host.ports != null && host.ports!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Open Ports (${host.ports!.length})',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  ...host.ports!.take(10).map((port) {
                    final isWebService = port.isWebService;
                    final portText = '${port.portNumber}/${port.protocol} - ${port.service ?? 'unknown'}${port.product != null ? ' (${port.product})' : ''}';
                    
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: isWebService
                          ? InkWell(
                              onTap: () {
                                final url = port.getUrl(host.ipAddress);
                                html.window.open(url, '_blank');
                              },
                              child: Row(
                                children: [
                                  const Icon(Icons.open_in_new, size: 12, color: Colors.blue),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      portText,
                                      style: const TextStyle(fontSize: 12, color: Colors.blue, decoration: TextDecoration.underline),
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : Text(portText, style: const TextStyle(fontSize: 12)),
                    );
                  }),
                  if (host.ports!.length > 10)
                    Text(
                      '... and ${host.ports!.length - 10} more',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Text(
            '$label: ',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
