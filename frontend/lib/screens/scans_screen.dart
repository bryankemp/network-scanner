import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/scan.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import 'scan_detail_screen.dart';
import 'create_scan_dialog.dart';
import 'hosts_list_screen.dart';
import 'services_list_screen.dart';

class ScansScreen extends StatefulWidget {
  const ScansScreen({super.key});

  @override
  State<ScansScreen> createState() => _ScansScreenState();
}

class _ScansScreenState extends State<ScansScreen> {
  final ApiService _apiService = ApiService();
  List<Scan> _scans = [];
  NetworkStats? _stats;
  bool _isLoading = true;
  String? _error;
  bool _isAdmin = false;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _isAdmin = AuthService().isAdmin();
    _loadData();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    // Refresh every 5 seconds if there are running scans
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (mounted && _hasRunningScans()) {
        _loadData();
      }
    });
  }

  bool _hasRunningScans() {
    return _scans.any((scan) => 
      scan.status.toLowerCase() == 'running' || 
      scan.status.toLowerCase() == 'pending'
    );
  }

  Future<void> _loadData() async {
    // Don't show loading spinner on auto-refresh
    final isInitialLoad = _scans.isEmpty;
    
    if (isInitialLoad) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final scans = await _apiService.getScans();
      final stats = await _apiService.getStats();
      
      if (mounted) {
        setState(() {
          _scans = scans;
          _stats = stats;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _createScan() async {
    final networks = await showDialog<List<String>>(
      context: context,
      builder: (context) => const CreateScanDialog(),
    );

    if (networks != null) {
      try {
        await _apiService.createScan(networks: networks.isEmpty ? null : networks);
        _loadData();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Scan created successfully')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to create scan: $e')),
          );
        }
      }
    }
  }

  Future<void> _deleteScan(int id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Scan'),
        content: const Text('Are you sure you want to delete this scan?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      try {
        await _apiService.deleteScan(id);
        _loadData();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Scan deleted')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to delete scan: $e')),
          );
        }
      }
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
        title: const Text('Network Scanner'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
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
                        onPressed: _loadData,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : Column(
                  children: [
                    if (_stats != null) _buildStatsCard(),
                    Expanded(
                      child: _scans.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Icon(Icons.radar, size: 64, color: Colors.grey),
                                  const SizedBox(height: 16),
                                  const Text('No scans yet'),
                                  const SizedBox(height: 16),
                                  if (_isAdmin)
                                    ElevatedButton.icon(
                                      onPressed: _createScan,
                                      icon: const Icon(Icons.add),
                                      label: const Text('Create First Scan'),
                                    ),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: _loadData,
                              child: ListView.builder(
                                itemCount: _scans.length,
                                itemBuilder: (context, index) {
                                  final scan = _scans[index];
                                  return _buildScanCard(scan);
                                },
                              ),
                            ),
                    ),
                  ],
                ),
      floatingActionButton: _isAdmin
          ? FloatingActionButton.extended(
              onPressed: _createScan,
              icon: const Icon(Icons.add),
              label: const Text('New Scan'),
            )
          : null,
    );
  }

  Widget _buildStatsCard() {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildStatItem(Icons.radar, 'Scans', _stats!.totalScans.toString(), null),
            _buildStatItem(Icons.devices, 'Hosts', _stats!.totalHosts.toString(), () {
              Navigator.push(context, MaterialPageRoute(
                builder: (context) => const HostsListScreen(),
              ));
            }),
            _buildStatItem(Icons.computer, 'VMs', _stats!.totalVms.toString(), () {
              Navigator.push(context, MaterialPageRoute(
                builder: (context) => const HostsListScreen(vmsOnly: true),
              ));
            }),
            _buildStatItem(Icons.settings_ethernet, 'Services', _stats!.totalServices.toString(), () {
              Navigator.push(context, MaterialPageRoute(
                builder: (context) => const ServicesListScreen(),
              ));
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(IconData icon, String label, String value, VoidCallback? onTap) {
    final widget = Column(
      children: [
        Icon(icon, size: 32, color: Theme.of(context).colorScheme.primary),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
    
    if (onTap == null) return widget;
    
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: widget,
      ),
    );
  }

  Widget _buildScanCard(Scan scan) {
    final dateFormat = DateFormat('MMM d, yyyy HH:mm');
    
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getStatusColor(scan.status),
          child: Icon(
            scan.status.toLowerCase() == 'completed'
                ? Icons.check
                : scan.status.toLowerCase() == 'failed'
                    ? Icons.error
                    : Icons.radar,
            color: Colors.white,
          ),
        ),
        title: Text(scan.networkRange),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text('Status: ${scan.status}'),
            if (scan.status.toLowerCase() == 'running')
              LinearProgressIndicator(value: scan.progressPercent / 100),
            Text('Created: ${dateFormat.format(scan.createdAt)}'),
            if (scan.totalHosts != null)
              Text('Hosts found: ${scan.totalHosts}'),
          ],
        ),
        trailing: PopupMenuButton(
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'view',
              child: Row(
                children: [
                  Icon(Icons.visibility),
                  SizedBox(width: 8),
                  Text('View Details'),
                ],
              ),
            ),
            if (_isAdmin)
              const PopupMenuItem(
                value: 'delete',
                child: Row(
                  children: [
                    Icon(Icons.delete, color: Colors.red),
                    SizedBox(width: 8),
                    Text('Delete', style: TextStyle(color: Colors.red)),
                  ],
                ),
              ),
          ],
          onSelected: (value) async {
            if (value == 'view') {
              await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => ScanDetailScreen(scanId: scan.id),
                ),
              );
              _loadData(); // Refresh data when returning
            } else if (value == 'delete') {
              _deleteScan(scan.id);
            }
          },
        ),
        onTap: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ScanDetailScreen(scanId: scan.id),
            ),
          );
          _loadData(); // Refresh data when returning
        },
      ),
    );
  }
}
