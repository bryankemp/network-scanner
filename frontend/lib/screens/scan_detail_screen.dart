import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:universal_html/html.dart' as html;
import 'dart:async';
import '../models/scan.dart';
import '../services/api_service.dart';

class ScanDetailScreen extends StatefulWidget {
  final int scanId;

  const ScanDetailScreen({super.key, required this.scanId});

  @override
  State<ScanDetailScreen> createState() => _ScanDetailScreenState();
}

class _ScanDetailScreenState extends State<ScanDetailScreen> {
  final ApiService _apiService = ApiService();
  Scan? _scan;
  bool _isLoading = true;
  String? _error;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadScan(showSpinner: true);
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (_scan?.status.toLowerCase() == 'running') {
        _loadScan();
      } else {
        timer.cancel();
      }
    });
  }

  Future<void> _loadScan({bool showSpinner = false}) async {
    if (showSpinner) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final scan = await _apiService.getScan(widget.scanId);
      if (mounted) {
        setState(() {
          _scan = scan;
          if (showSpinner) _isLoading = false; // keep UI stable during background refreshes
        });
        // Restart timer if scan is still running
        if (scan.status.toLowerCase() == 'running' && (_refreshTimer == null || !_refreshTimer!.isActive)) {
          _startAutoRefresh();
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          if (showSpinner) _isLoading = false;
        });
      }
    }
  }

  void _downloadArtifact(String type) {
    final url = _apiService.getArtifactUrl(widget.scanId, type);
    // For HTML, open in same tab. For downloads, open in new tab
    if (type.toLowerCase() == 'html') {
      html.window.location.href = url;
    } else {
      html.window.open(url, '_blank');
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return Colors.green;
      case 'failed':
        return Colors.red;
      case 'running':
        return Colors.blue;
      default:
        return Colors.orange;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadScan(showSpinner: false),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: Colors.red),
                      const SizedBox(height: 16),
                      Text('Error: $_error'),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadScan,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildScanInfo(),
                      const SizedBox(height: 24),
                      if (_scan!.status.toLowerCase() == 'running')
                        _buildProgressCard(),
                      if (_scan!.status.toLowerCase() == 'running')
                        const SizedBox(height: 24),
                      if (_scan!.status.toLowerCase() == 'running' && _scan!.hosts != null && _scan!.hosts!.isNotEmpty)
                        _buildHostProgressSection(),
                      if (_scan!.status.toLowerCase() == 'running' && _scan!.hosts != null && _scan!.hosts!.isNotEmpty)
                        const SizedBox(height: 24),
                      if (_scan!.artifacts != null && _scan!.artifacts!.isNotEmpty)
                        _buildArtifactsSection(),
                      const SizedBox(height: 24),
                      if (_scan!.hosts != null && _scan!.hosts!.isNotEmpty)
                        _buildHostsSection(),
                    ],
                  ),
                ),
    );
  }

  Widget _buildScanInfo() {
    final dateFormat = DateFormat('MMM d, yyyy HH:mm:ss');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.radar,
                  size: 32,
                  color: _getStatusColor(_scan!.status),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _scan!.networkRange,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      Text(
                        'Status: ${_scan!.status}',
                        style: TextStyle(
                          color: _getStatusColor(_scan!.status),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            _buildInfoRow('Scan ID', '#${_scan!.id}'),
            _buildInfoRow('Created', dateFormat.format(_scan!.createdAt)),
            if (_scan!.completedAt != null)
              _buildInfoRow('Completed', dateFormat.format(_scan!.completedAt!)),
            if (_scan!.totalHosts != null)
              _buildInfoRow('Hosts Found', _scan!.totalHosts.toString()),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  Widget _buildProgressCard() {
    return Card(
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.radar_outlined, color: Colors.blue, size: 32),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Scan in Progress',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: Colors.blue.shade900,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 250),
                        child: Text(
                          _scan!.progressMessage ?? 'Scanning...',
                          key: ValueKey(_scan!.progressMessage),
                          style: TextStyle(
                            color: Colors.blue.shade700,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: Text(
                    '${_scan!.progressPercent}%',
                    key: ValueKey(_scan!.progressPercent),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: Colors.blue.shade900,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: TweenAnimationBuilder<double>(
                duration: const Duration(milliseconds: 300),
                tween: Tween<double>(begin: 0, end: _scan!.progressPercent / 100),
                builder: (context, value, child) {
                  return LinearProgressIndicator(
                    value: value,
                    minHeight: 12,
                    backgroundColor: Colors.blue.shade100,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.blue.shade700),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Auto-refreshing every 2 seconds',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade600,
                    fontStyle: FontStyle.italic,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 20),
                  onPressed: _loadScan,
                  tooltip: 'Refresh now',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHostProgressSection() {
    // Filter to only show hosts that are scanning or pending (not completed/failed)
    final activeHosts = _scan!.hosts!.where((host) {
      final status = host.scanStatus?.toLowerCase() ?? 'pending';
      return status == 'scanning' || status == 'pending';
    }).toList();
    
    // If no active hosts, don't show this section
    if (activeHosts.isEmpty) {
      return const SizedBox.shrink();
    }
    
    // Sort hosts: scanning first, then pending
    activeHosts.sort((a, b) {
      final statusOrder = {'scanning': 0, 'pending': 1};
      final aOrder = statusOrder[a.scanStatus?.toLowerCase() ?? 'pending'] ?? 2;
      final bOrder = statusOrder[b.scanStatus?.toLowerCase() ?? 'pending'] ?? 2;
      return aOrder.compareTo(bOrder);
    });

    // Count hosts by status (for all hosts, not just active)
    final hostCounts = <String, int>{};
    for (var host in _scan!.hosts!) {
      final status = host.scanStatus?.toLowerCase() ?? 'pending';
      hostCounts[status] = (hostCounts[status] ?? 0) + 1;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.devices, size: 24),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Host Scanning Progress',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // Status summary
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                if (hostCounts['completed'] != null && hostCounts['completed']! > 0)
                  _buildStatusChip('Completed', hostCounts['completed']!, Colors.green),
                if (hostCounts['scanning'] != null && hostCounts['scanning']! > 0)
                  _buildStatusChip('Scanning', hostCounts['scanning']!, Colors.blue),
                if (hostCounts['pending'] != null && hostCounts['pending']! > 0)
                  _buildStatusChip('Pending', hostCounts['pending']!, Colors.orange),
                if (hostCounts['failed'] != null && hostCounts['failed']! > 0)
                  _buildStatusChip('Failed', hostCounts['failed']!, Colors.red),
              ],
            ),
            const Divider(height: 24),
            // Only show active (scanning/pending) hosts
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: activeHosts.length,
              separatorBuilder: (context, index) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final host = activeHosts[index];
                return _buildHostProgressItem(host);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusChip(String label, int count, Color color) {
    return Chip(
      avatar: CircleAvatar(
        backgroundColor: color,
        child: Text(
          count.toString(),
          style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
        ),
      ),
      label: Text(label),
      backgroundColor: color.withOpacity(0.1),
    );
  }

  Widget _buildHostProgressItem(Host host) {
    final status = host.scanStatus?.toLowerCase() ?? 'pending';
    
    // Determine icon and color based on status
    IconData icon;
    Color color;
    String statusText;
    
    switch (status) {
      case 'completed':
        icon = Icons.check_circle;
        color = Colors.green;
        statusText = 'Completed';
        break;
      case 'scanning':
        icon = Icons.sync;
        color = Colors.blue;
        statusText = 'Scanning...';
        break;
      case 'failed':
        icon = Icons.error;
        color = Colors.red;
        statusText = host.scanErrorMessage ?? 'Failed';
        break;
      default: // pending
        icon = Icons.schedule;
        color = Colors.orange;
        statusText = 'Waiting...';
    }

    // Build list of discovered details
    final details = <String>[];
    if (host.hostname != null && host.hostname!.isNotEmpty) {
      details.add('Hostname: ${host.hostname}');
    }
    if (host.mac != null && host.mac!.isNotEmpty) {
      details.add('MAC: ${host.mac}');
    }
    if (host.vendor != null && host.vendor!.isNotEmpty) {
      details.add('Vendor: ${host.vendor}');
    }
    if (host.osType != null && host.osType!.isNotEmpty) {
      details.add('OS: ${host.osType}');
    }
    if (host.isVm == true) {
      details.add('🖥️ Virtual Machine' + (host.vmType != null ? ' (${host.vmType})' : ''));
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      host.hostname ?? host.ipAddress,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (host.hostname != null)
                      Text(
                        host.ipAddress,
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                      ),
                  ],
                ),
              ),
              if (host.portsDiscovered != null && host.portsDiscovered! > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.blue.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.settings_ethernet, size: 14, color: Colors.blue),
                      const SizedBox(width: 4),
                      Text(
                        '${host.portsDiscovered}',
                        style: const TextStyle(fontSize: 12, color: Colors.blue, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          // Status and progress
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      statusText,
                      style: TextStyle(
                        fontSize: 12,
                        color: color,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    if (status == 'scanning' && host.scanProgressPercent != null)
                      const SizedBox(height: 4),
                    if (status == 'scanning' && host.scanProgressPercent != null)
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: TweenAnimationBuilder<double>(
                          duration: const Duration(milliseconds: 300),
                          tween: Tween<double>(
                            begin: 0,
                            end: (host.scanProgressPercent ?? 0) / 100,
                          ),
                          builder: (context, value, child) {
                            return LinearProgressIndicator(
                              value: value,
                              minHeight: 6,
                              backgroundColor: color.withOpacity(0.2),
                              valueColor: AlwaysStoppedAnimation<Color>(color),
                            );
                          },
                        ),
                      ),
                  ],
                ),
              ),
              if (status == 'scanning' && host.scanProgressPercent != null)
                const SizedBox(width: 8),
              if (status == 'scanning' && host.scanProgressPercent != null)
                Text(
                  '${host.scanProgressPercent}%',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
            ],
          ),
          // Discovered details
          if (details.isNotEmpty)
            const SizedBox(height: 8),
          if (details.isNotEmpty)
            Wrap(
              spacing: 12,
              runSpacing: 4,
              children: details.map((detail) => Text(
                detail,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey.shade700,
                ),
              )).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildArtifactsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Reports & Artifacts',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Click HTML to view the full report on this page',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _scan!.artifacts!.map((artifact) {
                IconData icon;
                Color color;
                String label;
                switch (artifact.type.toLowerCase()) {
                  case 'html':
                    icon = Icons.language;
                    color = Colors.orange;
                    label = 'VIEW HTML REPORT';
                    break;
                  case 'xlsx':
                    icon = Icons.table_chart;
                    color = Colors.green;
                    label = artifact.type.toUpperCase();
                    break;
                  case 'png':
                  case 'svg':
                    icon = Icons.image;
                    color = Colors.blue;
                    label = artifact.type.toUpperCase();
                    break;
                  default:
                    icon = Icons.file_present;
                    color = Colors.grey;
                    label = artifact.type.toUpperCase();
                }

                return ElevatedButton.icon(
                  onPressed: () => _downloadArtifact(artifact.type),
                  icon: Icon(icon, color: color),
                  label: Text(label),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHostsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Discovered Hosts (${_scan!.hosts!.length})',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _scan!.hosts!.length,
              itemBuilder: (context, index) {
                final host = _scan!.hosts![index];
                return _buildHostCard(host);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHostCard(Host host) {
    // Get appropriate icon based on vendor/OS
    IconData getDeviceIcon() {
      if (host.isVm == true) return Icons.computer;
      final vendor = host.vendor?.toLowerCase() ?? '';
      final os = host.osType?.toLowerCase() ?? '';
      
      if (vendor.contains('apple') || os.contains('ios') || os.contains('macos')) {
        return Icons.phone_iphone;
      } else if (vendor.contains('dell') || vendor.contains('hp') || vendor.contains('lenovo')) {
        return Icons.desktop_windows;
      } else if (vendor.contains('ubiquiti') || vendor.contains('cisco') || vendor.contains('netgear')) {
        return Icons.router;
      } else if (vendor.contains('ring') || vendor.contains('nest') || vendor.contains('camera')) {
        return Icons.videocam;
      } else if (vendor.contains('qemu') || vendor.contains('vmware') || vendor.contains('virtualbox')) {
        return Icons.dns;
      }
      return Icons.device_hub;
    }
    
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: ExpansionTile(
        leading: Icon(
          getDeviceIcon(),
          color: host.status.toLowerCase() == 'up' ? Colors.green : Colors.grey,
          size: 32,
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                host.hostname ?? host.ipAddress,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
            if (host.vendor != null && host.vendor!.isNotEmpty)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.business, size: 14, color: Colors.blue.shade700),
                    const SizedBox(width: 4),
                    Text(
                      host.vendor!,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.blue.shade700,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (host.hostname != null) 
                Text('IP: ${host.ipAddress}', style: TextStyle(color: Colors.grey.shade700)),
              if (host.mac != null && host.mac!.isNotEmpty)
                Text('MAC: ${host.mac}', style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
              if (host.osType != null && host.osType!.isNotEmpty) 
                Row(
                  children: [
                    Icon(Icons.info_outline, size: 14, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        host.osType!,
                        style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              if (host.isVm == true) 
                Row(
                  children: [
                    const Text('🖥️ ', style: TextStyle(fontSize: 14)),
                    Text(
                      'Virtual Machine${host.vmType != null && host.vmType!.isNotEmpty ? " (${host.vmType})" : ""}',
                      style: const TextStyle(color: Colors.blue, fontSize: 12),
                    ),
                  ],
                ),
            ],
          ),
        ),
        children: [
          if (host.ports != null && host.ports!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Open Ports (${host.ports!.length})',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  ...host.ports!.map((port) {
                    final serviceInfo = [
                      if (port.service != null) port.service!,
                      if (port.product != null) port.product!,
                      if (port.version != null) port.version!,
                    ].join(' ');
                    
                    return ListTile(
                      dense: true,
                      leading: Icon(
                        port.isWebService ? Icons.language : Icons.settings_ethernet,
                        size: 16,
                        color: port.isWebService ? Colors.blue : null,
                      ),
                      title: Row(
                        children: [
                          Text(
                            '${port.portNumber}/${port.protocol}',
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          if (port.isWebService)
                            const SizedBox(width: 8),
                          if (port.isWebService)
                            InkWell(
                              onTap: () {
                                final url = port.getUrl(host.ipAddress);
                                html.window.open(url, '_blank');
                              },
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.open_in_new, size: 14, color: Colors.blue),
                                  const SizedBox(width: 4),
                                  Text(
                                    'Open',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.blue.shade700,
                                      decoration: TextDecoration.underline,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                      subtitle: serviceInfo.isNotEmpty ? Text(serviceInfo) : null,
                    );
                  }),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
